# Campus Customs MCP Server

A FastMCP server that gives the Campus Customs agents (Boss, Inventory, Accounting, Facilities, Customer Service) every tool they use to read and change shop data.

- **Database:** the working copy `data/campus_customs_new.db`. The original `data/campus_customs.db` is only ever read, by `reset_db.py`.
- **Single access point:** the agents and the backend never open the database themselves; all shop data goes through these tools.
- **Shop date:** "today" always comes from `desk.date_today`.
- **No invented data:** tools return only what is in the database. Missing records come back as `{"found": false, "message": ...}`.
- **Reads vs. writes:** every tool is read-only except three that no agent is given: `record_approved_payment` (human-approved payments), `update_ticket_status`, and `reset_working_database_to_original`.

## Tools

- **`get_ticket(ticket_id)`**
  - Tables: `tickets`, `desk`
  - What it returns or does: One ticket exactly as stored, plus the shop date.
- **`list_open_tickets()`**
  - Tables: `tickets`, `desk`
  - What it returns or does: Every ticket with status `open`, plus the shop date.
- **`list_tickets()`**
  - Tables: `tickets`, `desk`
  - What it returns or does: Every ticket regardless of status, plus the shop date.
- **`update_ticket_status(ticket_id, status)`**
  - Tables: `tickets`
  - What it returns or does: **Backend only.** Sets a ticket to `open` or `resolved`; the backend calls it when the Boss decides a ticket is resolved.
- **`get_product_stock_and_pricing(sku, size=None)`**
  - Tables: `inventory`, `pricing`
  - What it returns or does: Quantity and location per size, plus `unit_cost` and `list_price`.
- **`evaluate_price_override(sku, quantity, proposed_unit_price)`**
  - Tables: `pricing`
  - What it returns or does: Revenue and margin at list price and at the proposed price, the discount, and `below_or_at_cost`. Only calculates; it approves nothing.
- **`list_vendors()`**
  - Tables: `vendors`, `invoices`, `desk`
  - What it returns or does: Every vendor's specialty, lead time, unpaid invoices, `can_ship_new_inventory`, and earliest arrival if ordered today (null when blocked).
- **`check_vendor_invoice_status(vendor_id=None, invoice_id=None)`**
  - Tables: `invoices`, `vendors`, `desk`
  - What it returns or does: One vendor's invoices with days overdue, the unpaid total, and `can_ship_new_inventory`. Give exactly one id; an invoice id is resolved to its vendor. Any status other than `paid` counts as unpaid.
- **`get_lease_rent_status(lease_id)`**
  - Tables: `leases`, `desk`
  - What it returns or does: Rent, landlord, next due date, `days_until_due`, `is_overdue`.
- **`get_cash_balance()`**
  - Tables: `cash_accounts`, `desk`
  - What it returns or does: Each cash account's balance and as-of date.
- **`get_payment_history(kind=None, ref_id=None)`**
  - Tables: `payments`, `desk`
  - What it returns or does: Payments already recorded, optionally filtered by `invoice`/`rent` and invoice or lease id.
- **`preview_payment_plan(payments, account=None)`**
  - Tables: `invoices`, `vendors`, `leases`, `cash_accounts`, `desk`
  - What it returns or does: For a list like `[{"kind": "invoice", "ref_id": 501}, {"kind": "rent", "ref_id": 1}]`: each amount and payee from the database, a running balance, and whether each payment can be made (rejects unknown ids, already-paid invoices, duplicates, and insufficient cash). Pays nothing.
- **`record_approved_payment(kind, ref_id, approved_by, account=None)`**
  - Tables: `cash_accounts`, `payments`, `invoices`, `leases`, `desk`
  - What it returns or does: **Human approval only; no agent is given this tool.** In one transaction it deducts the amount from cash (rejected if the balance would go negative), inserts a `payments` row dated `desk.date_today`, and marks the invoice `paid` or moves the lease's `next_due` forward one month. The amount always comes from the database. It rejects a blank approver or an AI agent's name.
- **`reset_working_database_to_original(confirm)`**
  - Tables: all tables
  - What it returns or does: **Operator only.** Restores the working database from the original in one locked transaction and verifies it. Refuses if another write is in progress. Does not touch the audit trail.

## Resetting the working database

```
.venv/bin/python -m mcp_server.reset_db
```

Restores every table of `data/campus_customs_new.db` from `data/campus_customs.db` in one locked transaction (the original is attached read-only), then confirms the contents match row for row. If another write is in progress it gives up after 5 seconds without changing anything. Run it before every full ticket-resolution run.

The same reset is available as the MCP tool `reset_working_database_to_original(confirm="RESET")` (operator only; no agent has it) and through the backend route `POST /api/database/reset`.

## Layout and adding tools

- `server.py`: creates the `FastMCP` server and registers all tools.
- `db.py`: database paths, the read-only connection, the locked write transaction, and `get_shop_date()`.
- `tools/`: one module per area (`tickets.py`, `inventory.py`, `invoices.py`, `leases.py`, `payments.py`, `maintenance.py`). Each module has a `register(mcp)` function.
- `reset_db.py`: the reset logic and script above.

To add a tool, write it inside a `register(mcp)` function in a new or existing module under `tools/`, and add any new module to `TOOL_MODULES` in `tools/__init__.py`. To let an agent use it, add its name to that agent's `mcp_tools` in `backend/team.py`.

## Running

From the Homework 5 folder: `.venv/bin/python -m mcp_server.server` (Claude Code starts it automatically from `.mcp.json`; the backend starts its own copy for each ticket run).
