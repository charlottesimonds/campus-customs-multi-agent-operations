"""Shared data types for the Campus Customs agent team."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]


# ---------------------------------------------------------------------------
# Ticket input
# ---------------------------------------------------------------------------


class Ticket(BaseModel):
    """One row of the tickets table, exactly as stored."""

    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    status: str
    notes: str | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Agent outputs
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    """A fact an agent relies on, with where it came from."""

    statement: str = Field(description="One verified fact, stated plainly with exact figures.")
    source: str = Field(
        description="The MCP tool or teammate that supplied it, e.g. 'check_vendor_invoice_status' "
        "or 'teammate:inventory'. Never 'assumption'."
    )


class ProposedAction(BaseModel):
    """An action the team recommends. Agents never execute these; a human decides."""

    kind: Literal[
        "payment", "purchase_order", "restock_order", "price_override", "lease_action", "fulfillment", "other"
    ]
    description: str = Field(description="What should happen, specifically.")
    amount: float | None = Field(default=None, description="Dollar amount if the action moves money; else null.")
    payee: str | None = Field(default=None, description="Who would receive the money, if any.")
    ref_table: str | None = Field(default=None, description="Database table the action refers to, e.g. 'invoices'.")
    ref_id: int | None = Field(default=None, description="Row id in ref_table, e.g. an invoice or lease id.")
    proposed_by: AgentName
    requires_human_approval: Literal[True] = Field(
        default=True, description="Always true: no action is carried out without human approval."
    )
    status: Literal["pending_approval"] = "pending_approval"


class DraftMessage(BaseModel):
    """A message written for a human to review. It is never sent by the system."""

    audience: Literal["customer", "vendor", "landlord", "internal"]
    to: str = Field(description="Recipient name exactly as it appears in the data.")
    subject: str
    body: str
    drafted_by: AgentName
    status: Literal["draft"] = "draft"


class AgentReport(BaseModel):
    """What any agent returns when it finishes a request from a teammate."""

    agent: AgentName
    summary: str = Field(description="Two or three sentences answering the request.")
    findings: list[Finding] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    drafts: list[DraftMessage] = Field(default_factory=list)
    open_questions: list[str] = Field(
        default_factory=list,
        description="Anything the agent could not verify from tools or teammates.",
    )


class TicketResolution(BaseModel):
    """The Boss's final decision on a ticket."""

    ticket_id: int
    decision: Literal["resolved", "awaiting_approval", "blocked", "needs_more_information"]
    summary: str = Field(description="Plain-language outcome for the shop owner.")
    rationale: str = Field(description="Why this decision, citing the findings it depends on.")
    findings: list[Finding] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    drafts: list[DraftMessage] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    outstanding_dependencies: list[str] = Field(
        default_factory=list,
        description="Things the ticket still depends on that are outside the shop's control and that this system "
        "cannot do (e.g. a vendor's delivery lead time, a customer's reply to a drafted message). List each one even "
        "when the decision is resolved.",
    )


# ---------------------------------------------------------------------------
# Run record (what the backend and dashboard will display)
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TeamEvent(BaseModel):
    """One audit record: a step of a ticket run, or a human/backend action (approval, reset).

    Every event is appended to output/audit_trail.json.
    """

    run_id: str | None = Field(default=None, description="Agent run this belongs to; null for actions outside a run.")
    ticket_id: int | None = None
    timestamp: str = Field(default_factory=_now)
    action: Literal[
        "run_started",
        "agent_started",
        "tool_called",
        "delegation_requested",
        "delegation_refused",
        "delegation_answered",
        "agent_finished",
        "run_completed",
        "run_failed",
        # Taken by the backend or a human, outside the agents' authority:
        "action_proposed",
        "action_approved",
        "action_rejected",
        "payment_recorded",
        "payment_failed",
        "ticket_status_updated",
        "database_reset",
    ]
    agent: AgentName | None = Field(
        default=None, description="Agent that took the step; null for steps taken by the backend or a human."
    )
    actor: str | None = Field(default=None, description="Human who took the step (approver), when there is one.")
    depth: int = Field(default=0, description="Delegation depth: 0 for the Boss, 1 for a teammate it asked, and so on.")
    chain: list[AgentName] = Field(default_factory=list, description="Who is waiting on whom, outermost first.")
    to_agent: AgentName | None = None
    tool_name: str | None = None
    tool_args: dict | None = None
    detail: str = Field(description="The request, prompt, reason, or summary for this step.")
    outcome: str | None = Field(default=None, description="Result of the step: tool output, decision, or error.")
    data: dict | None = Field(default=None, description="Structured details, e.g. a proposal or a final resolution.")


class UsageSummary(BaseModel):
    requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int


class TicketRunResult(BaseModel):
    run_id: str
    ticket: Ticket
    shop_date_today: str
    resolution: TicketResolution
    events: list[TeamEvent]
    delegations: int
    usage: UsageSummary
    models_used: list[str]
