"""The Campus Customs agent team: five PydanticAI agents with full connectivity.

Every agent can ask every other agent for help through the `ask_teammate` tool;
work does not have to route through the Boss. Delegation is guarded so a
ticket cannot loop forever:

- an agent cannot ask itself;
- an agent cannot ask anyone already upstream in the current chain
  (that agent is waiting on this answer, so asking it back would deadlock);
- chains stop at MAX_DELEGATION_DEPTH hops;
- a ticket allows at most MAX_DELEGATIONS_PER_TICKET delegations in total;
- all agent runs for one ticket share a single UsageLimits budget.

All shop data comes from the Campus Customs MCP server. This module never
opens the database; it only reasons, delegates, and coordinates. Every step is
appended to output/audit_trail.json.

Run one or more tickets from the Homework 5 folder:
    .venv/bin/python -m backend.team 101
"""

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models import Model
from pydantic_ai.usage import RunUsage

from . import audit
from .config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MODEL_SETTINGS,
    SERVED_MODEL_PREFIX,
    TICKET_USAGE_LIMITS,
    build_model,
)
from .models import (
    AgentName,
    AgentReport,
    TeamEvent,
    Ticket,
    TicketResolution,
    TicketRunResult,
    UsageSummary,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

AUDIT_OUTCOME_MAX_CHARS = 4_000


# ---------------------------------------------------------------------------
# Team roster. To add an agent: add a spec here and a prompt file in prompts/.
# To give an agent a new MCP tool: add the tool name to its mcp_tools.
# ---------------------------------------------------------------------------

# MCP tools that only the backend or a human may call: moving money (after human approval),
# changing ticket status, and resetting the database. No agent may ever hold them.
NON_AGENT_TOOLS = frozenset({"record_approved_payment", "update_ticket_status", "reset_working_database_to_original"})


@dataclass(frozen=True)
class AgentSpec:
    name: AgentName
    title: str
    expertise: str
    mcp_tools: frozenset[str]


AGENT_SPECS: dict[AgentName, AgentSpec] = {
    spec.name: spec
    for spec in [
        AgentSpec(
            "boss",
            "Boss",
            "triages tickets, coordinates the team, and makes final decisions",
            frozenset({"get_ticket", "list_open_tickets"}),
        ),
        AgentSpec(
            "inventory",
            "Inventory Manager",
            "stock by SKU and size, shortages, which vendor can restock, lead times, whether a vendor may ship",
            frozenset({"get_ticket", "get_product_stock_and_pricing", "list_vendors", "check_vendor_invoice_status"}),
        ),
        AgentSpec(
            "accounting",
            "Accountant",
            "cash, vendor invoices, payments, margins, discounts, purchase orders (prepares them for human approval)",
            frozenset(
                {
                    "get_ticket",
                    "get_cash_balance",
                    "get_payment_history",
                    "preview_payment_plan",
                    "check_vendor_invoice_status",
                    "list_vendors",
                    "get_product_stock_and_pricing",
                    "evaluate_price_override",
                    "get_lease_rent_status",
                }
            ),
        ),
        AgentSpec(
            "facilities",
            "Facilities Manager",
            "the shop space, lease terms, rent amounts and due dates, the landlord",
            frozenset({"get_ticket", "get_lease_rent_status", "get_payment_history", "preview_payment_plan"}),
        ),
        AgentSpec(
            "customer_service",
            "Customer Service",
            "drafts replies to customers and other requesters (drafts only, never sent)",
            frozenset({"get_ticket", "get_product_stock_and_pricing"}),
        ),
    ]
}

for _spec in AGENT_SPECS.values():
    if _spec.mcp_tools & NON_AGENT_TOOLS:
        raise RuntimeError(f"{_spec.name} must not be given non-agent tools: {_spec.mcp_tools & NON_AGENT_TOOLS}")

DELEGATION_TOOL = "ask_teammate"


class WrongModelError(RuntimeError):
    """Raised if any response was served by a model other than gpt-6-luna."""


class TicketNotFound(LookupError):
    pass


def _brief(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= AUDIT_OUTCOME_MAX_CHARS else text[:AUDIT_OUTCOME_MAX_CHARS] + "… [truncated]"


# ---------------------------------------------------------------------------
# Run state
# ---------------------------------------------------------------------------


@dataclass
class TicketRun:
    """State shared by every agent run while one ticket is being worked."""

    run_id: str
    ticket: Ticket
    shop_date: str
    events: list[TeamEvent] = field(default_factory=list)
    delegations: int = 0
    answers: list[str] = field(default_factory=list)  # teammate answers so far, shared to avoid repeat questions
    models_used: set[str] = field(default_factory=set)
    # Facts from outside this ticket that no MCP tool holds (the backend supplies them): other tickets'
    # payment requests awaiting approval, and human decisions already recorded on this ticket.
    shop_context: str = ""

    def log(self, *, chain: tuple[AgentName, ...] = (), **kwargs) -> None:
        """Record one step and append it to the audit trail immediately."""
        event = TeamEvent(
            run_id=self.run_id,
            ticket_id=self.ticket.id,
            chain=list(chain),
            depth=max(len(chain) - 1, 0),
            agent=chain[-1] if chain else None,
            **kwargs,
        )
        self.events.append(event)
        audit.append_records([event.model_dump(mode="json")])

    def context_block(self) -> str:
        block = (
            f"Shop date (desk.date_today): {self.shop_date}\n"
            f"Ticket being worked:\n{self.ticket.model_dump_json(indent=2)}"
        )
        if self.answers:
            block += "\n\nAnswers teammates have already given on this ticket (don't ask for these again):\n"
            block += "\n".join(f"- {answer}" for answer in self.answers)
        if self.shop_context:
            block += f"\n\n{self.shop_context}"
        return block


@dataclass(frozen=True)
class TeamDeps:
    run: TicketRun
    chain: tuple[AgentName, ...]  # outermost agent first; chain[-1] is the agent currently running

    @property
    def me(self) -> AgentName:
        return self.chain[-1]

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


# ---------------------------------------------------------------------------
# Instructions
# ---------------------------------------------------------------------------


def _team_section(spec: AgentSpec) -> str:
    teammates = "\n".join(
        f"- `{other.name}` ({other.title}): {other.expertise}"
        for other in AGENT_SPECS.values()
        if other.name != spec.name
    )
    tools = ", ".join(f"`{t}`" for t in sorted(spec.mcp_tools)) or "none; ask a teammate for any data you need"
    return f"""

## Your team

Use the `{DELEGATION_TOOL}` tool to ask any teammate for help. You do not need to go through the Boss.
{teammates}

## Delegating well

- Ask one specific, self-contained question and include the ids the teammate needs (SKU, size, quantity, invoice id, lease id). They see the ticket but not your conversation.
- Only ask when the answer needs their expertise or tools. Don't ask for something you already have.
- You can't ask yourself, or anyone already upstream in the current chain, because they are waiting on your answer. If a request is refused, finish with what you have and list the gap in `open_questions`.
- Chains stop at {MAX_DELEGATION_DEPTH} hops and a ticket allows {MAX_DELEGATIONS_PER_TICKET} delegations in total, so ask for everything you need from a teammate in one request.
- A teammate's answer is evidence you can cite with source `teammate:<name>`.

## Your shop-data tools

All shop data comes from these MCP tools. You have no other way to read or change the database.
{tools}

## Your answer

Return your answer with `agent` set to `{spec.name}`. Every finding needs a real source. Anything you could not verify belongs in `open_questions`.
"""


def build_mcp_toolset(process_tool_call=None) -> MCPToolset:
    """One connection to the Campus Customs MCP server, shared by all agents."""
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env={"PYTHONPATH": str(PROJECT_ROOT)},
        cwd=str(PROJECT_ROOT),
    )
    return MCPToolset(Client(transport), max_retries=2, process_tool_call=process_tool_call)


# ---------------------------------------------------------------------------
# The team
# ---------------------------------------------------------------------------


class CampusCustomsTeam:
    def __init__(self, model: Model | None = None):
        self.model = model or build_model()
        self.mcp = build_mcp_toolset(process_tool_call=self._audited_tool_call)
        self.agents: dict[AgentName, Agent[TeamDeps, AgentReport]] = {
            name: self._build_agent(spec) for name, spec in AGENT_SPECS.items()
        }

    def _build_agent(self, spec: AgentSpec) -> Agent[TeamDeps, AgentReport]:
        prompt = (PROMPTS_DIR / f"{spec.name}.md").read_text(encoding="utf-8")
        allowed = spec.mcp_tools
        tools = self.mcp.filtered(lambda ctx, tool_def: tool_def.name in allowed)

        async def ask_teammate(ctx: RunContext[TeamDeps], teammate: AgentName, request: str) -> dict:
            """Ask another Campus Customs agent to handle part of this ticket.

            Args:
                teammate: Which agent to ask.
                request: A specific, self-contained question including any ids they need.

            Returns the teammate's report (summary, findings, proposed actions, drafts,
            open questions), or a refusal explaining why the request was not delegated.
            """
            return await self._delegate(ctx, teammate, request)

        return Agent(
            self.model,
            name=spec.name,
            deps_type=TeamDeps,
            output_type=AgentReport,
            instructions=prompt + _team_section(spec),
            toolsets=[tools],
            tools=[ask_teammate],
            model_settings=MODEL_SETTINGS,
            retries=2,
        )

    # -- MCP tool calls ------------------------------------------------------

    async def _audited_tool_call(
        self, ctx: RunContext[TeamDeps], call_tool: CallToolFunc, name: str, args: dict[str, Any]
    ):
        """Every MCP call an agent makes passes through here: permission check, then audit."""
        deps = ctx.deps
        if name in NON_AGENT_TOOLS or name not in AGENT_SPECS[deps.me].mcp_tools:
            reason = f"{deps.me} is not permitted to call {name}."
            deps.run.log(chain=deps.chain, action="tool_called", tool_name=name, tool_args=args,
                         detail="blocked", outcome=reason)
            raise PermissionError(reason)
        try:
            result = await call_tool(name, args)
        except Exception as exc:
            deps.run.log(chain=deps.chain, action="tool_called", tool_name=name, tool_args=args,
                         detail="MCP tool call", outcome=f"error: {exc}")
            raise
        deps.run.log(chain=deps.chain, action="tool_called", tool_name=name, tool_args=args,
                     detail="MCP tool call", outcome=_brief(result))
        return result

    # -- delegation ----------------------------------------------------------

    def _refusal_reason(self, deps: TeamDeps, teammate: AgentName) -> str | None:
        if teammate not in AGENT_SPECS:
            return f"There is no teammate called {teammate!r}."
        if teammate == deps.me:
            return "You cannot delegate to yourself."
        if teammate in deps.chain:
            return (
                f"{teammate} is already upstream in this chain ({' -> '.join(deps.chain)}) and is waiting on you. "
                "Answer with what you have and list any gaps in open_questions."
            )
        if deps.depth >= MAX_DELEGATION_DEPTH:
            return f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached. Answer with what you have."
        if deps.run.delegations >= MAX_DELEGATIONS_PER_TICKET:
            return f"This ticket has used all {MAX_DELEGATIONS_PER_TICKET} delegations. Answer with what you have."
        return None

    async def _delegate(self, ctx: RunContext[TeamDeps], teammate: AgentName, request: str) -> dict:
        deps, run = ctx.deps, ctx.deps.run
        reason = self._refusal_reason(deps, teammate)
        if reason:
            run.log(chain=deps.chain, action="delegation_refused", to_agent=teammate, detail=request, outcome=reason)
            return {"delegated": False, "reason": reason}

        run.delegations += 1
        run.log(chain=deps.chain, action="delegation_requested", to_agent=teammate, detail=request)
        caller = AGENT_SPECS[deps.me].title
        prompt = (
            f"Request from {caller} (chain: {' -> '.join(deps.chain + (teammate,))}).\n\n"
            f"{run.context_block()}\n\nRequest:\n{request}"
        )
        child = TeamDeps(run, deps.chain + (teammate,))
        report = await self._run_agent(teammate, prompt, child, ctx.usage)
        run.log(chain=child.chain, action="delegation_answered", to_agent=deps.me, detail=request,
                outcome=report.summary)
        run.answers.append(f"{teammate} (asked by {deps.me}): {report.summary}")
        return {"delegated": True, "report": report.model_dump(mode="json")}

    # -- running agents ------------------------------------------------------

    async def _run_agent(self, name: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage, output_type=None):
        run = deps.run
        run.log(chain=deps.chain, action="agent_started", detail=prompt.rsplit("\n\n", 1)[-1])
        before = (usage.requests, usage.input_tokens, usage.output_tokens)
        try:
            result = await self.agents[name].run(
                prompt, deps=deps, usage=usage, usage_limits=TICKET_USAGE_LIMITS, output_type=output_type
            )
            for message in result.new_messages():
                if isinstance(message, ModelResponse):
                    self._check_model(message, run)
        except Exception as exc:
            run.log(chain=deps.chain, action="agent_finished", detail="failed", outcome=f"error: {exc}")
            raise
        output = result.output
        if isinstance(output, AgentReport):
            output.agent = name
        spent = (usage.requests - before[0], usage.input_tokens - before[1], usage.output_tokens - before[2])
        run.log(
            chain=deps.chain,
            action="agent_finished",
            detail=f"model requests {spent[0]}, input tokens {spent[1]}, output tokens {spent[2]} "
            "(includes teammates it asked)",
            outcome=_brief(output.model_dump(mode="json")),
        )
        return output

    @staticmethod
    def _check_model(message: ModelResponse, run: TicketRun) -> None:
        served = message.model_name or ""
        run.models_used.add(served)
        if not served.startswith(SERVED_MODEL_PREFIX):
            raise WrongModelError(f"Response served by {served!r}; only {SERVED_MODEL_PREFIX} is allowed.")

    # -- public entry points -------------------------------------------------

    async def _load_ticket(self, ticket_id: int) -> tuple[Ticket, str]:
        """Fetch the ticket through MCP, the same way the agents read data."""
        result = await self.mcp.direct_call_tool("get_ticket", {"ticket_id": ticket_id})
        if not result.get("found"):
            raise TicketNotFound(result.get("message", f"No ticket with id {ticket_id}."))
        return Ticket(**result["ticket"]), result["shop_date_today"]

    async def run_ticket(self, ticket_id: int, run_id: str | None = None, shop_context: str = "") -> TicketRunResult:
        """Have the Boss work one ticket with the team and return the decision and full event log."""
        usage = RunUsage()
        async with self.mcp:  # keep one MCP server process up for every agent on this ticket
            ticket, shop_date = await self._load_ticket(ticket_id)
            run = TicketRun(run_id=run_id or uuid.uuid4().hex[:12], ticket=ticket, shop_date=shop_date,
                            shop_context=shop_context)
            run.log(action="run_started", tool_name="get_ticket", tool_args={"ticket_id": ticket_id},
                    detail="Ticket loaded through MCP by the backend.", outcome=_brief(ticket.model_dump(mode="json")),
                    data={"shop_context": shop_context} if shop_context else None)
            prompt = (
                "A new ticket has arrived. Work it with your team and return your final resolution.\n\n"
                f"{run.context_block()}"
            )
            try:
                resolution = await self._run_agent("boss", prompt, TeamDeps(run, ("boss",)), usage, TicketResolution)
            except Exception as exc:
                run.log(action="run_failed", detail=type(exc).__name__, outcome=str(exc),
                        data={"error_type": type(exc).__name__, "delegations": run.delegations})
                raise
        resolution.ticket_id = ticket_id
        usage_summary = UsageSummary(
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        run.log(
            action="run_completed",
            detail=f"decision={resolution.decision}; delegations={run.delegations}; "
            f"usage={usage_summary.model_dump_json()}; models={sorted(run.models_used)}",
            outcome=resolution.summary,
            data={
                "decision": resolution.decision,
                "resolution": resolution.model_dump(mode="json"),
                "delegations": run.delegations,
                "usage": usage_summary.model_dump(),
                "models_used": sorted(run.models_used),
            },
        )
        return TicketRunResult(
            run_id=run.run_id,
            ticket=run.ticket,
            shop_date_today=run.shop_date,
            resolution=resolution,
            events=run.events,
            delegations=run.delegations,
            usage=usage_summary,
            models_used=sorted(run.models_used),
        )


async def _main(ticket_ids: list[int]) -> None:
    team = CampusCustomsTeam()
    for ticket_id in ticket_ids:
        result = await team.run_ticket(ticket_id)
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Campus Customs tickets through the agent team.")
    parser.add_argument("ticket_ids", nargs="+", type=int)
    asyncio.run(_main(parser.parse_args().ticket_ids))
