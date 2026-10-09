"""Cash and payment tools.

Business rules enforced here, not left to the agents:
- every payment needs a named human approver (record_approved_payment);
- a payment is rejected if it would make the cash balance negative;
- an invoice that is already paid cannot be paid again;
- the amount is always the amount in the database, never one supplied by a caller.

record_approved_payment is deliberately NOT given to any agent (see
backend/team.py). Agents can only preview payments; a human approves them.
"""

import calendar
from datetime import date
from typing import Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from ..db import get_shop_date, read_connection, rows_to_dicts, write_transaction

PaymentKind = Literal["invoice", "rent"]

# Names that identify an AI agent rather than a person. A payment approved by
# one of these is rejected.
NON_HUMAN_APPROVERS = {
    "boss", "inventory", "accounting", "facilities", "customer_service", "customer service",
    "agent", "ai", "assistant", "system", "bot",
}


class PaymentItem(BaseModel):
    kind: PaymentKind
    ref_id: int


def _add_one_month(d: date) -> date:
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _resolve_account(conn, account: str | None) -> dict | str:
    """Return the cash account row, or an error message."""
    if account is None:
        rows = conn.execute("SELECT name, balance, date FROM cash_accounts").fetchall()
        if len(rows) != 1:
            names = [r["name"] for r in rows]
            return f"Specify an account; the shop has {len(rows)} cash accounts: {names}."
        return dict(rows[0])
    row = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    return dict(row) if row else f"No cash account named {account!r}."


def _resolve_payment(conn, kind: PaymentKind, ref_id: int) -> dict:
    """Look up what is owed for an invoice or a lease's next rent installment."""
    if kind == "invoice":
        row = conn.execute(
            "SELECT i.id, i.amount, i.due_date, i.status, i.description, v.name AS vendor "
            "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (ref_id,),
        ).fetchone()
        if row is None:
            return {"kind": kind, "ref_id": ref_id, "payable": False, "reason": f"No invoice with id {ref_id}."}
        item = {
            "kind": kind, "ref_id": ref_id, "amount": row["amount"], "payee": row["vendor"],
            "due_date": row["due_date"], "status": row["status"], "description": row["description"],
        }
        if row["status"] == "paid":
            return {**item, "payable": False, "reason": f"Invoice {ref_id} is already paid."}
        return {**item, "payable": True}

    row = conn.execute("SELECT id, landlord, monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
    if row is None:
        return {"kind": kind, "ref_id": ref_id, "payable": False, "reason": f"No lease with id {ref_id}."}
    return {
        "kind": kind, "ref_id": ref_id, "amount": row["monthly_rent"], "payee": row["landlord"],
        "due_date": row["next_due"], "description": f"Rent installment due {row['next_due']}", "payable": True,
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_cash_balance() -> dict:
        """Return every cash account with its balance and as-of date, plus the shop's current date.

        The database records no incoming revenue, so this balance only goes down.
        """
        with read_connection() as conn:
            today = get_shop_date(conn)
            accounts = rows_to_dicts(conn.execute("SELECT name, balance, date FROM cash_accounts").fetchall())
        return {
            "shop_date_today": today.isoformat(),
            "accounts": accounts,
            "total_balance": sum(a["balance"] for a in accounts),
        }

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_payment_history(kind: PaymentKind | None = None, ref_id: int | None = None) -> dict:
        """List payments already recorded in the payments table, newest first.

        Use it to check whether an invoice or a rent installment has already
        been paid before proposing a payment. Filter by kind ("invoice" or
        "rent") and/or ref_id (the invoice id or lease id). An empty list means
        no matching payment has been recorded.
        """
        query = "SELECT id, kind, ref_id, amount, account, paid_at, approved_by FROM payments WHERE 1 = 1"
        params: list = []
        if kind is not None:
            query += " AND kind = ?"
            params.append(kind)
        if ref_id is not None:
            query += " AND ref_id = ?"
            params.append(ref_id)
        with read_connection() as conn:
            today = get_shop_date(conn)
            rows = rows_to_dicts(conn.execute(query + " ORDER BY paid_at DESC, id DESC", params).fetchall())
        return {"shop_date_today": today.isoformat(), "filters": {"kind": kind, "ref_id": ref_id}, "payments": rows}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def preview_payment_plan(payments: list[PaymentItem], account: str | None = None) -> dict:
        """Check whether one or more payments could be made, without paying anything.

        For each payment, looks up the amount owed in the database (an invoice's
        amount, or a lease's monthly rent) and the payee, then subtracts it from
        the cash balance in order. Reports the running balance, whether every
        payment fits without cash going negative, and any payment that cannot be
        made (unknown id, invoice already paid, insufficient cash).

        Every payment still needs human approval before it is made.

        Args:
            payments: Items like {"kind": "invoice", "ref_id": 501} or {"kind": "rent", "ref_id": 1}.
            account: Cash account name. May be omitted when the shop has only one account.
        """
        with read_connection() as conn:
            today = get_shop_date(conn)
            acct = _resolve_account(conn, account)
            if isinstance(acct, str):
                return {"ok": False, "message": acct}
            items = [_resolve_payment(conn, p.kind, p.ref_id) for p in payments]

        balance = acct["balance"]
        seen: set[tuple[str, int]] = set()
        for item in items:
            key = (item["kind"], item["ref_id"])
            if key in seen and item["payable"]:
                item.update(payable=False, reason="Duplicate of an earlier item in this plan.")
            seen.add(key)
            if not item["payable"]:
                continue
            if item["amount"] > balance:
                item.update(
                    payable=False,
                    reason=f"Insufficient cash: needs {item['amount']:.2f}, {balance:.2f} available at this point.",
                )
                continue
            balance -= item["amount"]
            item["balance_after"] = balance

        payable = [i for i in items if i["payable"]]
        return {
            "ok": True,
            "shop_date_today": today.isoformat(),
            "account": acct["name"],
            "starting_balance": acct["balance"],
            "items": items,
            "total_of_payable_items": sum(i["amount"] for i in payable),
            "ending_balance_if_all_payable_items_paid": balance,
            "all_items_payable": len(payable) == len(items),
            "requires_human_approval": True,
        }

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False))
    def record_approved_payment(
        kind: PaymentKind, ref_id: int, approved_by: str, account: str | None = None
    ) -> dict:
        """Make a payment that a human has approved, and record it in the database.

        HUMAN APPROVAL ONLY: call this only after a named person has approved the
        payment. AI agents are not given this tool.

        In one transaction: deducts the amount owed from the cash account
        (rejected if the balance would go negative), inserts a row in payments,
        and marks an invoice "paid" or moves a lease's next_due forward one month.
        The amount always comes from the database.

        Args:
            kind: "invoice" or "rent".
            ref_id: The invoice id or lease id being paid.
            approved_by: Name of the person who approved the payment.
            account: Cash account name. May be omitted when the shop has only one account.
        """
        approver = approved_by.strip()
        if not approver:
            return {"status": "rejected", "reason": "approved_by is required: payments need a named human approver."}
        if approver.lower() in NON_HUMAN_APPROVERS:
            return {"status": "rejected", "reason": f"{approver!r} is not a human approver."}

        with write_transaction() as conn:
            today = get_shop_date(conn)
            acct = _resolve_account(conn, account)
            if isinstance(acct, str):
                return {"status": "rejected", "reason": acct}
            item = _resolve_payment(conn, kind, ref_id)
            if not item["payable"]:
                return {"status": "rejected", "reason": item["reason"]}

            amount = item["amount"]
            # The balance check and the deduction are one statement, so cash can never go negative.
            updated = conn.execute(
                "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ? AND balance >= ?",
                (amount, today.isoformat(), acct["name"], amount),
            ).rowcount
            if updated != 1:
                return {
                    "status": "rejected",
                    "reason": f"Insufficient cash: payment of {amount:.2f} exceeds the {acct['name']} "
                    f"balance of {acct['balance']:.2f}.",
                }

            payment_id = conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                (kind, ref_id, amount, acct["name"], today.isoformat(), approver),
            ).lastrowid

            if kind == "invoice":
                conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
                follow_up = {"invoice_status": "paid"}
            else:
                new_due = _add_one_month(date.fromisoformat(item["due_date"])).isoformat()
                conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, ref_id))
                follow_up = {"lease_next_due": new_due}

            balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (acct["name"],)).fetchone()[0]

        return {
            "status": "paid",
            "payment": {
                "id": payment_id, "kind": kind, "ref_id": ref_id, "amount": amount, "payee": item["payee"],
                "account": acct["name"], "paid_at": today.isoformat(), "approved_by": approver,
            },
            "balance_after": balance,
            **follow_up,
        }
