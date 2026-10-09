"""Lease and rent tools."""

from datetime import date

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..db import get_shop_date, read_connection, rows_to_dicts


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_lease_rent_status(lease_id: int) -> dict:
        """Look up a lease's rent amount, landlord, next due date, and recorded rent payments.

        Returns the lease record plus days_until_due and is_overdue, both
        measured against the shop's current date in desk.date_today, and every
        rent payment recorded against this lease. next_due is always the next
        UNPAID installment: recording an approved rent payment moves next_due
        forward one month.

        Args:
            lease_id: Lease id from the leases table (e.g. from a ticket).
        """
        with read_connection() as conn:
            today = get_shop_date(conn)
            row = conn.execute(
                "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
                "FROM leases WHERE id = ?",
                (lease_id,),
            ).fetchone()

            payments = rows_to_dicts(conn.execute(
                "SELECT id, amount, paid_at, approved_by FROM payments WHERE kind = 'rent' AND ref_id = ? ORDER BY id",
                (lease_id,),
            ).fetchall())

        if row is None:
            return {"found": False, "message": f"No lease with id {lease_id}."}

        lease = dict(row)
        days_until_due = (date.fromisoformat(lease["next_due"]) - today).days
        return {
            "found": True,
            "shop_date_today": today.isoformat(),
            "lease": lease,
            "days_until_due": days_until_due,
            "is_overdue": days_until_due < 0,
            "rent_payments_recorded": payments,
            "how_next_due_works": "next_due is the next unpaid installment. Each recorded rent payment pays the "
            "installment that was due at the time and moves next_due forward one month.",
        }
