"""Campus Customs FastAPI backend.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000

The backend receives requests, runs the agent team, manages human approvals, and
returns JSON. All shop data is read and changed through the Campus Customs MCP
server; this app never opens the database.

Every error response has the same shape:
    {"error": {"code": "ticket_not_found", "message": "...", "details": {...}}}
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Lets `uvicorn main:app` run from backend/ while the code imports the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Query, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from backend.service import ApiError, CampusCustomsOps  # noqa: E402

ops: CampusCustomsOps | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ops
    ops = CampusCustomsOps()
    await ops.start()
    try:
        yield
    finally:
        await ops.stop()


app = FastAPI(
    title="Campus Customs Backend",
    version="1.0.0",
    description="Tickets, agent runs, activity, human approvals, cash, and reset for the Campus Customs agent team.",
    lifespan=lifespan,
)

# The React dashboard will be served by its own dev server (Vite on 5173 or CRA on 3000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Errors: one JSON shape for everything
# ---------------------------------------------------------------------------


def _error(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


@app.exception_handler(ApiError)
async def _api_error(request: Request, exc: ApiError):
    return _error(exc.status, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    return _error(422, "invalid_request", "The request is missing fields or has values of the wrong type.",
                  {"errors": exc.errors()})


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return _error(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def _unexpected_error(request: Request, exc: Exception):
    return _error(500, "internal_error", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the person approving.")
    note: str | None = Field(default=None, description="Optional instructions or conditions attached to the approval.")


class RejectRequest(BaseModel):
    rejected_by: str = Field(min_length=1, description="Name of the person rejecting.")
    reason: str | None = None


class ResetRequest(BaseModel):
    confirm: str = Field(description='Must be exactly "RESET".')
    requested_by: str = Field(min_length=1, description="Name of the person resetting the database.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["system"])
async def health():
    """Backend is up and connected to the MCP server."""
    return await ops.health()


@app.get("/api/tickets", tags=["tickets"])
async def list_tickets():
    """Every ticket with its database status, latest agent run, and pending approvals."""
    return await ops.list_tickets()


@app.get("/api/tickets/{ticket_id}", tags=["tickets"])
async def get_ticket(ticket_id: int):
    """One ticket with all of its runs and proposed actions."""
    return await ops.get_ticket(ticket_id)


@app.post("/api/tickets/{ticket_id}/run", status_code=202, tags=["runs"])
async def run_ticket(ticket_id: int):
    """Start the agent team on a ticket. Returns immediately; follow progress via /api/activity or /api/runs/{run_id}."""
    return await ops.start_run(ticket_id)


@app.get("/api/runs", tags=["runs"])
async def list_runs():
    """Every agent run, newest first: running, completed, failed, or interrupted."""
    return await ops.list_runs()


@app.get("/api/runs/{run_id}", tags=["runs"])
async def get_run(run_id: str):
    """One run's status, the Boss's final resolution, and the actions it proposed."""
    return await ops.get_run(run_id)


@app.get("/api/activity", tags=["activity"])
async def activity(
    after: int | None = Query(None, ge=-1, description="Return records after this cursor (seq). Omit for the latest."),
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
):
    """Agent activity straight from output/audit_trail.json. Poll with ?after=<next_cursor> for new records."""
    return await ops.activity(after, limit, ticket_id, run_id)


@app.get("/api/approvals", tags=["approvals"])
async def list_approvals(
    status: str | None = Query(None, description="pending, paid, approved, rejected, failed, stale, superseded, invalid"),
    ticket_id: int | None = None,
):
    """Actions agents proposed, with their review status."""
    return await ops.list_proposals(status, ticket_id)


@app.get("/api/approvals/{proposal_id}", tags=["approvals"])
async def get_approval(proposal_id: str):
    """One proposed action and what the database said about it when it was proposed."""
    return await ops.get_proposal(proposal_id)


@app.post("/api/approvals/{proposal_id}/approve", tags=["approvals"])
async def approve(proposal_id: str, body: ApproveRequest):
    """A human approves a proposed action. Payments are re-verified, then recorded through MCP."""
    return await ops.approve(proposal_id, body.approved_by, body.note)


@app.post("/api/approvals/{proposal_id}/reject", tags=["approvals"])
async def reject(proposal_id: str, body: RejectRequest):
    """A human rejects a proposed action. Nothing changes in the database."""
    return await ops.reject(proposal_id, body.rejected_by, body.reason)


@app.get("/api/cash", tags=["cash"])
async def cash():
    """Current checking balance from cash_accounts."""
    return await ops.cash()


@app.post("/api/database/reset", tags=["system"])
async def reset_database(body: ResetRequest):
    """Restore data/campus_customs_new.db from data/campus_customs.db. Refused while a run or write is in progress."""
    return await ops.reset(body.confirm, body.requested_by)
