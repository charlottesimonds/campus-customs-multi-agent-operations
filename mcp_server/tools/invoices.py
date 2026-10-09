"""Vendor and vendor-invoice tools."""

from datetime import date, timedelta

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from ..db import get_shop_date, read_connection

# Any invoice whose status is not "paid" counts as unpaid. This is the
# conservative reading: an unknown status blocks shipping rather than allowing it.
PAID_STATUS = "paid"


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def check_vendor_invoice_status(
        vendor_id: int | None = None, invoice_id: int | None = None
    ) -> dict:
        """Check a vendor's invoices and whether that vendor may ship new inventory.

        Shop rule: a vendor with any unpaid invoice cannot ship new inventory.
        Returns the vendor (name, specialty, lead_days), every invoice for that
        vendor with days overdue measured against desk.date_today, the unpaid
        total, and can_ship_new_inventory. An invoice counts as unpaid unless
        its status is exactly "paid".

        Provide exactly one of:
            vendor_id: Vendor id from the vendors table.
            invoice_id: Invoice id (e.g. from a ticket); its vendor is looked up.
        """
        if (vendor_id is None) == (invoice_id is None):
            raise ToolError("Provide exactly one of vendor_id or invoice_id.")

        with read_connection() as conn:
            today = get_shop_date(conn)

            if invoice_id is not None:
                invoice_row = conn.execute(
                    "SELECT vendor_id FROM invoices WHERE id = ?", (invoice_id,)
                ).fetchone()
                if invoice_row is None:
                    return {"found": False, "message": f"No invoice with id {invoice_id}."}
                vendor_id = invoice_row["vendor_id"]

            vendor_row = conn.execute(
                "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
            ).fetchone()
            if vendor_row is None:
                return {"found": False, "message": f"No vendor with id {vendor_id}."}

            invoice_rows = conn.execute(
                "SELECT id, vendor_id, amount, due_date, status, description "
                "FROM invoices WHERE vendor_id = ? ORDER BY due_date",
                (vendor_id,),
            ).fetchall()

        invoices = []
        for row in invoice_rows:
            invoice = dict(row)
            unpaid = invoice["status"] != PAID_STATUS
            days_past_due = (today - date.fromisoformat(invoice["due_date"])).days
            invoice["is_unpaid"] = unpaid
            invoice["is_overdue"] = unpaid and days_past_due > 0
            invoice["days_overdue"] = days_past_due if invoice["is_overdue"] else 0
            invoices.append(invoice)

        unpaid_invoices = [inv for inv in invoices if inv["is_unpaid"]]
        return {
            "found": True,
            "shop_date_today": today.isoformat(),
            "vendor": dict(vendor_row),
            "invoices": invoices,
            "unpaid_invoice_ids": [inv["id"] for inv in unpaid_invoices],
            "total_unpaid": sum(inv["amount"] for inv in unpaid_invoices),
            "can_ship_new_inventory": not unpaid_invoices,
        }

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def list_vendors() -> dict:
        """List every vendor with its specialty, lead time, and whether it may ship new inventory.

        A vendor with any unpaid invoice cannot ship. For vendors that can ship,
        earliest_arrival_if_ordered_today is desk.date_today + lead_days; for a
        blocked vendor it is null. The database does not link products to
        vendors, so match products to vendors by specialty and say so.
        """
        with read_connection() as conn:
            today = get_shop_date(conn)
            vendor_rows = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
            unpaid_rows = conn.execute(
                "SELECT id, vendor_id, amount FROM invoices WHERE status != ?", (PAID_STATUS,)
            ).fetchall()

        vendors = []
        for row in vendor_rows:
            unpaid = [r for r in unpaid_rows if r["vendor_id"] == row["id"]]
            can_ship = not unpaid
            vendors.append(
                {
                    **dict(row),
                    "unpaid_invoice_ids": [r["id"] for r in unpaid],
                    "total_unpaid": sum(r["amount"] for r in unpaid),
                    "can_ship_new_inventory": can_ship,
                    "earliest_arrival_if_ordered_today": (
                        (today + timedelta(days=row["lead_days"])).isoformat() if can_ship else None
                    ),
                }
            )
        return {"shop_date_today": today.isoformat(), "vendors": vendors}
