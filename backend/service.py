"""Operations behind the HTTP API: tickets, agent runs, activity, approvals, cash, and reset.

Rules this module keeps:
- Shop data is only read or changed through MCP tools; nothing here opens the database.
- Agents can only propose actions. A payment is made only when a human approves a
  proposal that an agent run actually produced, and only after re-checking (through MCP)
  that it is unpaid, unchanged, and covered by cash. record_approved_payment re-checks
  the balance atomically as well.
- History lives in output/audit_trail.json. Proposals, approvals, rejections, payments,
  and resets are appended there, so pending approvals survive a server restart and
  nothing is ever erased.
"""

import asyncio
import re
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from . import audit
from .config import MODEL_NAME
from .models import ProposedAction, TeamEvent, TicketRunResult
from .team import AGENT_SPECS, CampusCustomsTeam

# A payment proposal must point at one of these tables; the value is the MCP payment kind.
PAYMENT_REF_KINDS = {"invoices": "invoice", "leases": "rent"}
NON_HUMAN_NAMES = {name.lower() for name in AGENT_SPECS} | {
    "customer service", "agent", "ai", "assistant", "system", "bot", "boss",
}
RESET_CONFIRMATION = "RESET"
AMOUNT_TOLERANCE = 0.005


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ActiveRun:
    run_id: str
    ticket_id: int
    started_at: str
    task: asyncio.Task | None = None


class CampusCustomsOps:
    def __init__(self) -> None:
        self.team = CampusCustomsTeam()
        self.mcp = self.team.mcp
        self.active_runs: dict[str, ActiveRun] = {}
        # Serializes everything that changes shop data or run state: registering a run,
        # approving a payment, and resetting. A reset can never cut into an approval.
        self.lock = asyncio.Lock()
        self._stack = AsyncExitStack()

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        await self._stack.enter_async_context(self.mcp)  # one MCP server process for the app's lifetime

    async def stop(self) -> None:
        for run in list(self.active_runs.values()):
            if run.task:
                run.task.cancel()
        await asyncio.gather(*(r.task for r in self.active_runs.values() if r.task), return_exceptions=True)
        await self._stack.aclose()

    # -- helpers -------------------------------------------------------------

    async def _call(self, tool: str, args: dict | None = None) -> Any:
        try:
            return await self.mcp.direct_call_tool(tool, args or {})
        except Exception as exc:
            raise ApiError(502, "mcp_tool_failed", f"MCP tool {tool!r} failed: {exc}") from exc

    @staticmethod
    def _record(action: str, **fields) -> dict:
        event = TeamEvent(action=action, **fields).model_dump(mode="json")
        audit.append_records([event])
        return event

    @staticmethod
    def _records() -> list[dict]:
        try:
            records = audit.read_records()
        except audit.AuditTrailCorrupted as exc:
            raise ApiError(500, "audit_trail_corrupted", str(exc)) from exc
        return [{"seq": i, **r} for i, r in enumerate(records)]

    @staticmethod
    def _check_human(name: str, field: str) -> str:
        name = (name or "").strip()
        if not name:
            raise ApiError(422, "approver_required", f"{field} must name the person taking this action.")
        if name.lower() in NON_HUMAN_NAMES:
            raise ApiError(422, "approver_not_human", f"{name!r} is not a human approver.")
        return name

    async def _get_ticket(self, ticket_id: int) -> dict:
        result = await self._call("get_ticket", {"ticket_id": ticket_id})
        if not result.get("found"):
            raise ApiError(404, "ticket_not_found", result.get("message", f"No ticket with id {ticket_id}."))
        return result

    # -- health ----------------------------------------------------------------

    async def health(self) -> dict:
        tools = await self.mcp.client.list_tools()
        shop = await self._call("list_tickets")
        return {
            "status": "ok",
            "model": MODEL_NAME,
            "mcp_tools": sorted(t.name for t in tools),
            "shop_date_today": shop["shop_date_today"],
            "active_runs": len(self.active_runs),
        }

    # -- runs (derived from the audit trail) ----------------------------------

    def _runs(self, records: list[dict]) -> dict[str, dict]:
        last_reset = max((r["seq"] for r in records if r["action"] == "database_reset"), default=-1)
        runs: dict[str, dict] = {}
        for r in records:
            run_id = r.get("run_id")
            if not run_id:
                continue
            if r["action"] == "run_started":
                runs[run_id] = {
                    "run_id": run_id, "ticket_id": r["ticket_id"], "started_at": r["timestamp"],
                    "finished_at": None, "status": "interrupted", "decision": None, "summary": None,
                    "error": None, "before_last_reset": r["seq"] < last_reset, "_seq": r["seq"],
                }
            elif run_id in runs and r["action"] == "run_completed":
                data = r.get("data") or {}
                # Runs recorded before Problem 7 kept the decision only in the detail text.
                legacy = re.search(r"decision=(\w+)", r.get("detail") or "")
                decision = data.get("decision") or (legacy.group(1) if legacy else None)
                runs[run_id]["outstanding_dependencies"] = (data.get("resolution") or {}).get("outstanding_dependencies", [])
                runs[run_id].update(status="completed", finished_at=r["timestamp"], decision=decision,
                                    summary=r.get("outcome"), usage=data.get("usage"),
                                    delegations=data.get("delegations"), models_used=data.get("models_used"),
                                    _resolution=data.get("resolution"))
            elif run_id in runs and r["action"] == "run_failed" and runs[run_id]["status"] != "completed":
                runs[run_id].update(status="failed", finished_at=r["timestamp"], error=r.get("outcome"))
        for run_id, active in self.active_runs.items():
            runs.setdefault(run_id, {"run_id": run_id, "ticket_id": active.ticket_id, "started_at": active.started_at,
                                     "finished_at": None, "decision": None, "summary": None, "error": None,
                                     "before_last_reset": False, "_seq": len(records)})
            runs[run_id]["status"] = "running"
        return runs

    @staticmethod
    def _public(run: dict) -> dict:
        return {k: v for k, v in run.items() if not k.startswith("_")}

    async def list_runs(self) -> dict:
        runs = sorted(self._runs(self._records()).values(), key=lambda r: r["_seq"], reverse=True)
        return {"runs": [self._public(r) for r in runs]}

    async def get_run(self, run_id: str) -> dict:
        records = self._records()
        run = self._runs(records).get(run_id)
        if run is None:
            raise ApiError(404, "run_not_found", f"No run with id {run_id!r}.")
        proposals = [p for p in self._proposals(records).values() if p["run_id"] == run_id]
        run_records = [r for r in records if r.get("run_id") == run_id]
        return {**self._public(run), "resolution": run.get("_resolution"), "proposals": proposals,
                "contributions": self._contributions(run_records, run.get("_resolution")),
                "event_count": len(run_records)}

    @staticmethod
    def _contributions(run_records: list[dict], resolution: dict | None) -> list[dict]:
        """What each agent did in one run, taken only from that run's audit records."""
        agents: dict[str, dict] = {}

        def entry(name: str) -> dict:
            return agents.setdefault(name, {"agent": name, "asked_by": [], "requests": [], "tools_used": {},
                                            "delegated_to": [], "refused_delegations": 0, "summary": None,
                                            "proposed_actions": [], "drafts": []})

        for r in run_records:
            action, agent = r["action"], r.get("agent")
            if action == "agent_started" and agent:
                entry(agent)
            elif action == "tool_called" and agent:
                tools = entry(agent)["tools_used"]
                tools[r["tool_name"]] = tools.get(r["tool_name"], 0) + 1
            elif action == "delegation_requested" and agent:
                entry(agent)["delegated_to"].append(r["to_agent"])
                target = entry(r["to_agent"])
                target["asked_by"].append(agent)
                target["requests"].append(r.get("detail"))
            elif action == "delegation_refused" and agent:
                entry(agent)["refused_delegations"] += 1
            elif action == "delegation_answered" and agent:
                entry(agent)["summary"] = r.get("outcome")  # the agent's own answer; last one wins
            elif action == "run_completed":
                entry("boss")["summary"] = r.get("outcome")
            elif action == "action_proposed" and agent:
                entry(agent)["proposed_actions"].append((r.get("data") or {}).get("description"))
        for draft in (resolution or {}).get("drafts", []):
            entry(draft["drafted_by"])["drafts"].append({"audience": draft["audience"], "to": draft["to"],
                                                         "subject": draft["subject"]})
        return list(agents.values())

    async def start_run(self, ticket_id: int) -> dict:
        ticket = (await self._get_ticket(ticket_id))["ticket"]
        if ticket["status"] != "open":
            raise ApiError(409, "ticket_not_open", f"Ticket {ticket_id} is {ticket['status']!r}; only open tickets can be run.")
        async with self.lock:
            busy = next((r for r in self.active_runs.values() if r.ticket_id == ticket_id), None)
            if busy:
                raise ApiError(409, "run_in_progress", f"Ticket {ticket_id} already has a run in progress.",
                               {"run_id": busy.run_id})
            run = ActiveRun(run_id=uuid.uuid4().hex[:12], ticket_id=ticket_id, started_at=_now())
            self.active_runs[run.run_id] = run
            run.task = asyncio.create_task(self._execute_run(run))
        return {"run_id": run.run_id, "ticket_id": ticket_id, "status": "running", "started_at": run.started_at}

    async def _execute_run(self, run: ActiveRun) -> None:
        try:
            result = await self.team.run_ticket(run.ticket_id, run_id=run.run_id,
                                                shop_context=self._shop_context(run.ticket_id))
            await self._register_proposals(result)
            if result.resolution.decision == "resolved":
                update = await self._call("update_ticket_status", {"ticket_id": run.ticket_id, "status": "resolved"})
                self._record("ticket_status_updated", run_id=run.run_id, ticket_id=run.ticket_id,
                             tool_name="update_ticket_status", detail="Boss decided the ticket is resolved.",
                             outcome=f"{update.get('previous_status')} -> {update.get('status')}", data=update)
        except asyncio.CancelledError:
            self._record("run_failed", run_id=run.run_id, ticket_id=run.ticket_id, detail="Cancelled",
                         outcome="The server stopped before the run finished.")
            raise
        except Exception as exc:
            mine = [r["action"] for r in audit.read_records() if r.get("run_id") == run.run_id]
            if "run_failed" not in mine:  # the team logs failures inside the agent run itself
                self._record("run_failed", run_id=run.run_id, ticket_id=run.ticket_id, detail=type(exc).__name__,
                             outcome=getattr(exc, "message", str(exc)),
                             data={"error_type": type(exc).__name__, "after_completion": "run_completed" in mine})
        finally:
            self.active_runs.pop(run.run_id, None)

    # -- proposals -------------------------------------------------------------

    def _shop_context(self, ticket_id: int) -> str:
        """What the team must know that no MCP tool holds: requests and decisions living in the audit trail."""
        # Only what happened since the last reset is true of the current database.
        proposals = [p for p in self._proposals(self._records()).values() if not p["before_last_reset"]]

        def line(p: dict) -> str:
            v = (p.get("verification") or {}).get("verified") or {}
            due = f", installment due {v['due_date']}" if v.get("kind") == "rent" and v.get("due_date") else (
                f", due {v['due_date']}" if v.get("due_date") else "")
            target = f" ({v['kind']} {v['ref_id']}{due}, {v['amount']:.2f} to {v['payee']})" if v.get("amount") is not None else ""
            return f"{p['kind']}: {p['description']}{target}"

        sections = []
        other = [p for p in proposals if p["status"] == "pending" and p["kind"] == "payment" and p["ticket_id"] != ticket_id]
        if other:
            sections.append(
                "Payment requests from OTHER tickets awaiting human approval. Nothing has been paid yet, but if approved "
                "they draw on the same checking account, so treat them as committed when judging what cash is free:\n"
                + "\n".join(f"- Ticket {p['ticket_id']}: {line(p)}" for p in other))
        decided = [p for p in proposals if p["ticket_id"] == ticket_id and p["status"] in ("paid", "approved", "rejected", "failed")]
        if decided:
            verb = {"paid": "APPROVED and PAID (recorded in payments)", "approved": "APPROVED (decision recorded; no database change)",
                    "rejected": "DECLINED", "failed": "APPROVED but NOT PAID (refused)"}
            sections.append(
                "Human decisions already recorded on THIS ticket (build on these; do not propose them again):\n"
                + "\n".join(f"- {verb[p['status']]} by {p['decided_by']}: {line(p)}"
                             + (f" — note: {p['decision_note']}" if p.get("decision_note") else "") for p in decided))
        return "\n\n".join(sections)

    async def _register_proposals(self, result: TicketRunResult) -> None:
        """Record each action the Boss proposed so a human can review it."""
        seen: set[tuple] = set()
        for action in result.resolution.proposed_actions:
            key = (
                ("payment", action.ref_table, action.ref_id) if action.kind == "payment"
                else (action.kind, action.ref_table, action.ref_id, action.amount, action.description.strip().lower())
            )
            if key in seen:
                continue
            seen.add(key)
            proposal = {"proposal_id": uuid.uuid4().hex[:12], "run_id": result.run_id,
                        "ticket_id": result.ticket.id, **action.model_dump(mode="json")}
            proposal["verification"] = (
                await self._verify_payment(action) if action.kind == "payment"
                else {"approvable": True, "executes_on_approval": False, "problems": [],
                      "note": "No MCP tool records this kind of action; approval records the human decision only."}
            )
            self._record("action_proposed", run_id=result.run_id, ticket_id=result.ticket.id,
                         agent=action.proposed_by, detail=action.description, data=proposal)

    async def _verify_payment(self, action: ProposedAction) -> dict:
        """Snapshot what the database says this payment is, so approval can detect any change."""
        problems: list[str] = []
        kind = PAYMENT_REF_KINDS.get(action.ref_table or "")
        if kind is None or action.ref_id is None:
            return {"approvable": False, "executes_on_approval": False,
                    "problems": ["Payment does not reference an invoice id (invoices) or lease id (leases)."]}
        preview = await self._call("preview_payment_plan", {"payments": [{"kind": kind, "ref_id": action.ref_id}]})
        item = preview["items"][0] if preview.get("ok") else {}
        if "amount" not in item:
            problems.append(item.get("reason") or preview.get("message") or "Payment target not found.")
        elif action.amount is None or abs(action.amount - item["amount"]) > AMOUNT_TOLERANCE:
            problems.append(f"Proposed amount {action.amount} does not match the database amount {item['amount']}.")
        return {
            "approvable": not problems,
            "executes_on_approval": not problems,
            "problems": problems,
            "verified": {
                "kind": kind, "ref_id": action.ref_id, "amount": item.get("amount"), "payee": item.get("payee"),
                "due_date": item.get("due_date"), "payable_when_proposed": item.get("payable"),
                "reason_if_not_payable": item.get("reason"), "balance_after_if_paid": item.get("balance_after"),
                "checked_at_shop_date": preview.get("shop_date_today"),
            },
        }

    def _proposals(self, records: list[dict]) -> dict[str, dict]:
        last_reset = max((r["seq"] for r in records if r["action"] == "database_reset"), default=-1)
        latest_run_for_ticket: dict[int, str] = {}
        proposals: dict[str, dict] = {}
        for r in records:
            data = r.get("data") or {}
            if r["action"] == "run_completed":
                latest_run_for_ticket[r["ticket_id"]] = r["run_id"]
            if r["action"] == "action_proposed":
                approvable = data.get("verification", {}).get("approvable", False)
                proposals[data["proposal_id"]] = {
                    **data, "status": "pending" if approvable else "invalid", "proposed_at": r["timestamp"],
                    "decided_by": None, "decided_at": None, "decision_note": None, "result": None, "_seq": r["seq"],
                }
                continue
            p = proposals.get(data.get("proposal_id"))
            if p is None:
                continue
            if r["action"] == "action_rejected":
                p.update(status="rejected", decided_by=r.get("actor"), decided_at=r["timestamp"], decision_note=r.get("outcome"))
            elif r["action"] == "action_approved":
                p.update(status="approved", decided_by=r.get("actor"), decided_at=r["timestamp"], decision_note=data.get("note"))
            elif r["action"] == "payment_recorded":
                p.update(status="paid", result=data.get("payment_result"))
            elif r["action"] == "payment_failed" and data.get("final", True):
                p.update(status="failed", decided_by=r.get("actor"), decided_at=r["timestamp"],
                         decision_note=r.get("outcome"), result={"code": data.get("code")})
            elif r["action"] == "payment_failed":  # transient error: nothing was paid, the human may retry
                p.update(status="pending", decision_note=r.get("outcome"))
        for p in proposals.values():
            p["before_last_reset"] = p["_seq"] < last_reset
            if p["status"] == "pending" and p["_seq"] < last_reset:
                p["status"] = "stale"
                p["decision_note"] = "Proposed before the database was reset."
            elif p["status"] == "pending" and latest_run_for_ticket.get(p["ticket_id"], p["run_id"]) != p["run_id"]:
                p["status"] = "superseded"
                p["decision_note"] = "A newer run of this ticket replaced this proposal."
        return {pid: {k: v for k, v in p.items() if not k.startswith("_")} for pid, p in proposals.items()}

    async def list_proposals(self, status: str | None = None, ticket_id: int | None = None) -> dict:
        proposals = list(self._proposals(self._records()).values())
        if status:
            proposals = [p for p in proposals if p["status"] == status]
        if ticket_id is not None:
            proposals = [p for p in proposals if p["ticket_id"] == ticket_id]
        return {"approvals": sorted(proposals, key=lambda p: p["proposed_at"], reverse=True)}

    async def get_proposal(self, proposal_id: str) -> dict:
        proposal = self._proposals(self._records()).get(proposal_id)
        if proposal is None:
            raise ApiError(404, "approval_not_found",
                           f"No proposed action with id {proposal_id!r}. Only actions proposed by an agent run can be approved.")
        return proposal

    def _require_pending(self, proposal: dict) -> None:
        status = proposal["status"]
        if status == "pending":
            return
        codes = {"paid": "already_paid", "approved": "already_decided", "rejected": "already_decided",
                 "failed": "already_decided", "stale": "stale_proposal", "superseded": "stale_proposal",
                 "invalid": "invalid_proposal"}
        raise ApiError(409, codes.get(status, "not_pending"),
                       f"Proposal {proposal['proposal_id']} is {status}; only pending proposals can be decided.",
                       {"status": status, "decision_note": proposal.get("decision_note")})

    async def approve(self, proposal_id: str, approved_by: str, note: str | None = None) -> dict:
        approver = self._check_human(approved_by, "approved_by")
        note = (note or "").strip() or None
        async with self.lock:
            proposal = await self.get_proposal(proposal_id)
            self._require_pending(proposal)
            ids = {"run_id": proposal["run_id"], "ticket_id": proposal["ticket_id"]}

            if proposal["kind"] != "payment":
                self._record("action_approved", **ids, actor=approver, detail=proposal["description"],
                             outcome="Approved. No database change: no MCP tool records this kind of action."
                             + (f" Note: {note}" if note else ""),
                             data={"proposal_id": proposal_id, "executed": False, "note": note})
                return {"proposal_id": proposal_id, "status": "approved", "executed": False,
                        "message": "Decision recorded. This kind of action is carried out outside the system."}

            verified = proposal["verification"]["verified"]
            kind, ref_id = verified["kind"], verified["ref_id"]

            def fail(code: str, message: str, status: int = 409):
                self._record("payment_failed", **ids, actor=approver, tool_name="record_approved_payment",
                             tool_args={"kind": kind, "ref_id": ref_id}, detail=code, outcome=message,
                             data={"proposal_id": proposal_id, "code": code, "final": True})
                raise ApiError(status, code, message, {"proposal_id": proposal_id})

            history = await self._call("get_payment_history", {"kind": kind, "ref_id": ref_id})
            if kind == "invoice" and history["payments"]:
                fail("already_paid", f"Invoice {ref_id} already has a recorded payment.")
            preview = await self._call("preview_payment_plan", {"payments": [{"kind": kind, "ref_id": ref_id}]})
            item = preview["items"][0]
            if kind == "rent" and item.get("due_date") != verified["due_date"]:
                fail("already_paid", f"The rent installment due {verified['due_date']} has already been paid; "
                                     f"the lease is now due {item.get('due_date')}.")
            if "amount" in item and abs(item["amount"] - verified["amount"]) > AMOUNT_TOLERANCE:
                fail("amount_changed", f"Amount owed changed from {verified['amount']} to {item['amount']} since it was proposed.")
            if not item.get("payable"):
                reason = item.get("reason", "Not payable.")
                code = ("already_paid" if "already paid" in reason.lower()
                        else "insufficient_cash" if "insufficient cash" in reason.lower() else "not_payable")
                fail(code, reason)

            self._record("action_approved", **ids, actor=approver, detail=proposal["description"],
                         outcome=f"Approved payment of {verified['amount']:.2f} to {verified['payee']}."
                         + (f" Note: {note}" if note else ""),
                         data={"proposal_id": proposal_id, "executed": True, "note": note})
            try:
                result = await self._call("record_approved_payment",
                                          {"kind": kind, "ref_id": ref_id, "approved_by": approver})
            except ApiError as exc:
                # The MCP call itself failed. record_approved_payment is a single transaction, and a retry
                # re-checks payment history and balance first, so retrying cannot pay twice.
                self._record("payment_failed", **ids, actor=approver, tool_name="record_approved_payment",
                             tool_args={"kind": kind, "ref_id": ref_id}, detail=exc.code, outcome=exc.message,
                             data={"proposal_id": proposal_id, "code": exc.code, "final": False})
                raise
            if result.get("status") != "paid":
                reason = result.get("reason", "Payment was not recorded.")
                fail("insufficient_cash" if "insufficient cash" in reason.lower() else "payment_rejected", reason)
            self._record("payment_recorded", **ids, actor=approver, tool_name="record_approved_payment",
                         tool_args={"kind": kind, "ref_id": ref_id, "approved_by": approver},
                         detail=proposal["description"],
                         outcome=f"Paid {result['payment']['amount']:.2f}; balance now {result['balance_after']:.2f}.",
                         data={"proposal_id": proposal_id, "payment_result": result})
            return {"proposal_id": proposal_id, "status": "paid", "executed": True, **result}

    async def reject(self, proposal_id: str, rejected_by: str, reason: str | None) -> dict:
        person = self._check_human(rejected_by, "rejected_by")
        async with self.lock:
            proposal = await self.get_proposal(proposal_id)
            self._require_pending(proposal)
            self._record("action_rejected", run_id=proposal["run_id"], ticket_id=proposal["ticket_id"], actor=person,
                         detail=proposal["description"], outcome=reason or "Rejected.",
                         data={"proposal_id": proposal_id})
        return {"proposal_id": proposal_id, "status": "rejected", "executed": False}

    # -- tickets ---------------------------------------------------------------

    def _ticket_view(self, ticket: dict, runs: dict[str, dict], proposals: dict[str, dict]) -> dict:
        ticket_runs = sorted((r for r in runs.values() if r["ticket_id"] == ticket["id"]), key=lambda r: r["_seq"])
        latest = self._public(ticket_runs[-1]) if ticket_runs else None
        pending = [p["proposal_id"] for p in proposals.values()
                   if p["ticket_id"] == ticket["id"] and p["status"] == "pending"]
        return {**ticket, "latest_run": latest, "pending_approval_ids": pending,
                "is_running": any(r.ticket_id == ticket["id"] for r in self.active_runs.values())}

    async def list_tickets(self) -> dict:
        data = await self._call("list_tickets")
        records = self._records()
        runs, proposals = self._runs(records), self._proposals(records)
        return {"shop_date_today": data["shop_date_today"],
                "tickets": [self._ticket_view(t, runs, proposals) for t in data["tickets"]]}

    async def get_ticket(self, ticket_id: int) -> dict:
        data = await self._get_ticket(ticket_id)
        records = self._records()
        runs, proposals = self._runs(records), self._proposals(records)
        view = self._ticket_view(data["ticket"], runs, proposals)
        view["runs"] = [self._public(r) for r in sorted(runs.values(), key=lambda r: r["_seq"], reverse=True)
                        if r["ticket_id"] == ticket_id]
        view["approvals"] = [p for p in proposals.values() if p["ticket_id"] == ticket_id]
        return {"shop_date_today": data["shop_date_today"], "ticket": view}

    # -- activity ---------------------------------------------------------------

    async def activity(self, after: int | None, limit: int, ticket_id: int | None, run_id: str | None) -> dict:
        records = self._records()
        selected = [r for r in records
                    if (ticket_id is None or r.get("ticket_id") == ticket_id)
                    and (run_id is None or r.get("run_id") == run_id)]
        if after is not None:
            selected = [r for r in selected if r["seq"] > after][:limit]
        else:
            selected = selected[-limit:]
        return {
            "records": selected,
            "next_cursor": selected[-1]["seq"] if selected else (after if after is not None else len(records) - 1),
            "total_records": len(records),
            "active_runs": [{"run_id": r.run_id, "ticket_id": r.ticket_id, "started_at": r.started_at}
                            for r in self.active_runs.values()],
        }

    # -- cash --------------------------------------------------------------------

    async def cash(self) -> dict:
        data = await self._call("get_cash_balance")
        checking = next((a for a in data["accounts"] if a["name"] == "checking"), None)
        if checking is None:
            raise ApiError(404, "account_not_found", "No cash account named 'checking'.", {"accounts": data["accounts"]})
        return {"account": "checking", "balance": checking["balance"], "as_of": checking["date"],
                "shop_date_today": data["shop_date_today"], "accounts": data["accounts"],
                "proposed_payments": await self._proposed_payments(checking["balance"])}

    async def _proposed_payments(self, balance: float) -> dict:
        """Pending payment proposals previewed through MCP. Nothing here moves money."""
        pending = sorted((p for p in self._proposals(self._records()).values()
                          if p["status"] == "pending" and p["kind"] == "payment"), key=lambda p: p["proposed_at"])
        summary = {"count": len(pending), "total_payable": 0.0, "balance_if_all_approved": balance,
                   "all_fit": True, "items": [],
                   "note": "Proposed payments have not moved any money. Only an approved, recorded payment changes the balance."}
        if not pending:
            return summary
        targets = [{"kind": p["verification"]["verified"]["kind"], "ref_id": p["verification"]["verified"]["ref_id"]}
                   for p in pending]
        plan = await self._call("preview_payment_plan", {"payments": targets})
        for proposal, target, planned in zip(pending, targets, plan["items"]):
            alone = (await self._call("preview_payment_plan", {"payments": [target]}))["items"][0]
            summary["items"].append({
                "proposal_id": proposal["proposal_id"], "ticket_id": proposal["ticket_id"],
                "description": proposal["description"], "proposed_by": proposal["proposed_by"],
                "payee": planned.get("payee"), "amount": planned.get("amount"),
                "payable_alone": alone.get("payable", False), "balance_after_alone": alone.get("balance_after"),
                "reason_alone": alone.get("reason"),
                "payable_in_plan": planned.get("payable", False), "balance_after_in_plan": planned.get("balance_after"),
                "reason_in_plan": planned.get("reason"),
            })
        summary.update(total_payable=plan["total_of_payable_items"],
                       balance_if_all_approved=plan["ending_balance_if_all_payable_items_paid"],
                       all_fit=plan["all_items_payable"])
        return summary

    # -- reset ---------------------------------------------------------------------

    async def reset(self, confirm: str, requested_by: str) -> dict:
        person = self._check_human(requested_by, "requested_by")
        if confirm != RESET_CONFIRMATION:
            raise ApiError(400, "confirmation_required", f'Send "confirm": "{RESET_CONFIRMATION}" to reset the working database.')
        async with self.lock:  # waits for any approval in progress; blocks new runs from registering
            if self.active_runs:
                raise ApiError(409, "run_in_progress", "Cannot reset while an agent run is in progress.",
                               {"active_runs": [r.run_id for r in self.active_runs.values()]})
            result = await self._call("reset_working_database_to_original", {"confirm": RESET_CONFIRMATION})
            if result.get("status") == "busy":
                raise ApiError(409, "database_busy", result.get("reason", "Database busy; reset not started."))
            if result.get("status") != "reset":
                raise ApiError(500, "reset_failed", result.get("reason", "Reset did not complete."))
            self._record("database_reset", actor=person, tool_name="reset_working_database_to_original",
                         detail="Working database restored from the original.",
                         outcome="Verified identical to data/campus_customs.db. Audit trail kept.", data=result)
        return {**result, "audit_trail": "kept", "requested_by": person}
