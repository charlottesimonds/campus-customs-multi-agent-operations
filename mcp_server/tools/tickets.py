"""Ticket tools."""

from typing import Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..db import get_shop_date, read_connection, rows_to_dicts, write_transaction


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_ticket(ticket_id: int) -> dict:
        """Look up one ticket exactly as stored, plus the shop's current date.

        Returns every field of the ticket (type, requester, subject, sku, size,
        qty, lease_id, invoice_id, status, notes, created_at) and
        shop_date_today from desk.date_today.

        Args:
            ticket_id: Ticket id from the tickets table, e.g. 101.
        """
        with read_connection() as conn:
            today = get_shop_date(conn)
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "message": f"No ticket with id {ticket_id}."}
        return {"found": True, "shop_date_today": today.isoformat(), "ticket": dict(row)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def list_open_tickets() -> dict:
        """List every ticket whose status is "open", oldest id first, plus the shop's current date."""
        with read_connection() as conn:
            today = get_shop_date(conn)
            rows = conn.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY id").fetchall()
        return {"shop_date_today": today.isoformat(), "tickets": rows_to_dicts(rows)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def list_tickets() -> dict:
        """List every ticket regardless of status (open, resolved, ...), oldest id first, plus the shop's current date."""
        with read_connection() as conn:
            today = get_shop_date(conn)
            rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        return {"shop_date_today": today.isoformat(), "tickets": rows_to_dicts(rows)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))
    def update_ticket_status(ticket_id: int, status: Literal["open", "resolved"]) -> dict:
        """Set a ticket's status to "open" or "resolved".

        BACKEND ONLY: AI agents are not given this tool. The backend calls it
        when the Boss decides a ticket is resolved with nothing left waiting.

        Args:
            ticket_id: Ticket id.
            status: "open" or "resolved".
        """
        with write_transaction() as conn:
            row = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            if row is None:
                return {"found": False, "message": f"No ticket with id {ticket_id}."}
            conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        return {"found": True, "ticket_id": ticket_id, "previous_status": row["status"], "status": status}
