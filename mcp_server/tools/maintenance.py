"""Maintenance tools for the operator, never for agents."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..reset_db import DatabaseBusy, reset_working_database

CONFIRMATION = "RESET"


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True))
    def reset_working_database_to_original(confirm: str) -> dict:
        """Restore data/campus_customs_new.db to match data/campus_customs.db exactly.

        OPERATOR ONLY: AI agents are not given this tool. Discards every change
        made to the working copy (payments, balances, ticket statuses). The
        original database is attached read-only and never modified, and the
        audit trail is not touched. If another write is in progress the reset
        is refused rather than interrupting it.

        Args:
            confirm: Must be exactly "RESET".
        """
        if confirm != CONFIRMATION:
            return {"status": "rejected", "reason": f'confirm must be exactly "{CONFIRMATION}".'}
        try:
            return {"status": "reset", **reset_working_database()}
        except DatabaseBusy as exc:
            return {"status": "busy", "reason": str(exc)}
