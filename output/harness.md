# Campus Customs Harness

Sections are in the order they were built. **The Problem 9 section is the complete, current reference**; earlier sections describe the system as it stood at that problem and are kept as a record.

## Problem 2: Database structure

Source: `data/campus_customs.db` (original, unchanged). Working copy: `data/campus_customs_new.db`.

### Problem 2 · desk
- **Fields:** `date_today`, `notes`
- **Why it matters:** Supplies the shop's "today" date that every agent must use to judge what is due or overdue.

### Problem 2 · tickets
- **Fields:** `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
- **Why it matters:** The work queue the Boss triages and delegates; its `sku`/`size`, `lease_id`, and `invoice_id` point the agents to the data each ticket needs.

### Problem 2 · inventory
- **Fields:** `sku`, `name`, `size`, `qty`, `location`
- **Why it matters:** Lets the Inventory agent check stock by SKU and size and spot shortages.

### Problem 2 · pricing
- **Fields:** `sku`, `unit_cost`, `list_price`
- **Why it matters:** Gives Accounting the cost and price per SKU needed to calculate margins and evaluate discount requests.

### Problem 2 · vendors
- **Fields:** `id`, `name`, `specialty`, `lead_days`
- **Why it matters:** Tells the Inventory agent who can restock which kind of product and how many days delivery takes.

### Problem 2 · leases
- **Fields:** `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
- **Why it matters:** Gives the Facilities agent the rent amount and due date for the shop space.

### Problem 2 · cash_accounts
- **Fields:** `name`, `balance`, `date`
- **Why it matters:** The cash Accounting checks before proposing any payment, since balances can never go negative.

### Problem 2 · payments
- **Fields:** `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
- **Why it matters:** The ledger where completed, human-approved payments must be recorded (currently empty).

### Problem 2 · invoices
- **Fields:** `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
- **Why it matters:** Shows what the shop owes vendors; an unpaid invoice blocks that vendor from shipping new inventory.

## Problem 3: MCP tools

Server: `mcp_server/` (FastMCP), reading the working copy `data/campus_customs_new.db` read-only.

### Problem 3 · get_product_stock_and_pricing
- **Reads:** `inventory`, `pricing`
- **Ticket:** 103
- **Why:** The Yale AI Club wants 20 size-M hoodies at a bulk discount, so the agents need the on-hand count for `CC-HOOD-NAVY` size M (8, leaving 12 short) and its $22 unit cost against the $58 list price to know how much discount the shop can afford.

### Problem 3 · check_vendor_invoice_status
- **Reads:** `invoices`, `vendors`, `desk`
- **Ticket:** 101
- **Why:** Size-S tees are out of stock, and the ticket's linked invoice 501 ($840, "Rush reprint CC-TEE-WHITE S") is unpaid and 3 days overdue as of `desk.date_today`, so this tool shows its vendor, Bulldog Print Co, cannot ship the restock until that invoice is paid.

### Problem 3 · get_lease_rent_status
- **Reads:** `leases`, `desk`
- **Ticket:** 102
- **Why:** Elm City Properties' rent notice needs the actual amount owed ($2,400) and the due date (2026-09-02, 2 days after `desk.date_today`) so Facilities and Accounting can prepare the rent payment for human approval before it becomes overdue.

## Problem 5: Agent team, full MCP toolset, audit trail, and safety

The team is built with PydanticAI in `backend/` (`team.py`, `models.py`, `prompts/`). Every agent uses `gpt-6-luna` through Portkey, and a run stops if any response comes from a different model. Any agent can ask any other agent for help with the `ask_teammate` tool, so work does not have to go through the Boss.

### Problem 5 · Agents

- **Boss**
  - Responsibilities: Reads each ticket, decides which teammates it needs, checks their answers against each other, and makes the final decision (`resolved`, `awaiting_approval`, `blocked`, or `needs_more_information`). Never approves payments itself.
  - MCP tools it can call: `get_ticket`, `list_open_tickets`
- **Inventory**
  - Responsibilities: Checks stock by SKU and size, states shortfalls, matches a restock vendor by specialty, and confirms the vendor has no unpaid invoice before recommending a restock and its earliest arrival date.
  - MCP tools it can call: `get_ticket`, `get_product_stock_and_pricing`, `list_vendors`, `check_vendor_invoice_status`
- **Accounting**
  - Responsibilities: Verifies cash, invoices, and payment history. Previews every payment so cash cannot go negative. Calculates margins for discount requests. Proposes payments for human approval and cannot make them.
  - MCP tools it can call: `get_ticket`, `get_cash_balance`, `get_payment_history`, `preview_payment_plan`, `check_vendor_invoice_status`, `list_vendors`, `get_product_stock_and_pricing`, `evaluate_price_override`, `get_lease_rent_status`
- **Facilities**
  - Responsibilities: Handles the lease: rent amount, due date, and landlord. Checks whether rent is already paid, prepares the rent payment for approval, and drafts landlord replies.
  - MCP tools it can call: `get_ticket`, `get_lease_rent_status`, `get_payment_history`, `preview_payment_plan`
- **Customer Service**
  - Responsibilities: Drafts replies to customers and other requesters using only verified facts. Drafts are never sent.
  - MCP tools it can call: `get_ticket`, `get_product_stock_and_pricing`

### Problem 5 · All MCP tools

*As of Problem 5 (11 tools). Problem 7 added `list_tickets`, `update_ticket_status`, and `reset_working_database_to_original`, and Problem 9 extended `get_lease_rent_status`. See the Problem 9 reference for all 14.*

The MCP server is the only way the agents and the backend reach `data/campus_customs_new.db`. The backend even loads tickets through `get_ticket`.

- **`get_ticket`**
  - Tables: `tickets`, `desk`
  - Access: read
  - Used for: All tickets: one ticket's details plus the shop date
- **`list_open_tickets`**
  - Tables: `tickets`, `desk`
  - Access: read
  - Used for: Listing the queue
- **`get_product_stock_and_pricing` *(Problem 3)***
  - Tables: `inventory`, `pricing`
  - Access: read
  - Used for: 101, 103: stock by size, unit cost, list price
- **`evaluate_price_override`**
  - Tables: `pricing`
  - Access: read
  - Used for: 103: margin and revenue at list vs. proposed price; flags prices at or below cost
- **`list_vendors`**
  - Tables: `vendors`, `invoices`, `desk`
  - Access: read
  - Used for: 101, 103: every vendor's specialty, lead time, whether it can ship, and earliest arrival date
- **`check_vendor_invoice_status` *(Problem 3)***
  - Tables: `invoices`, `vendors`, `desk`
  - Access: read
  - Used for: 101, 103: a vendor's invoices, days overdue, and whether it can ship
- **`get_lease_rent_status` *(Problem 3)***
  - Tables: `leases`, `desk`
  - Access: read
  - Used for: 102: rent amount, due date, and days until due
- **`get_cash_balance`**
  - Tables: `cash_accounts`, `desk`
  - Access: read
  - Used for: 101, 102: cash available before any payment
- **`get_payment_history`**
  - Tables: `payments`, `desk`
  - Access: read
  - Used for: 101, 102: whether an invoice or rent installment is already paid
- **`preview_payment_plan`**
  - Tables: `invoices`, `vendors`, `leases`, `cash_accounts`, `desk`
  - Access: read
  - Used for: 101, 102: running balance across one or more payments, with each payment marked payable or not
- **`record_approved_payment`**
  - Tables: `cash_accounts`, `payments`, `invoices`, `leases`, `desk`
  - Access: **write**
  - Used for: Human approval only, and no agent can call it. In one transaction it deducts cash (rejected if the balance would go negative), records the payment, and marks the invoice paid or moves the lease's `next_due` forward one month.

`mcp_server/reset_db.py` (a script, not a tool) copies the original database over the working copy before a full run.

### Problem 5 · Audit trail

Each step of every run is appended to `output/audit_trail.json` as it happens. Records are never overwritten, and a file lock keeps simultaneous runs from clobbering each other. Each record has:
- `run_id`, `ticket_id`, and `timestamp`;
- `action`: `run_started`, `agent_started`, `tool_called`, `delegation_requested`, `delegation_refused`, `delegation_answered`, `agent_finished`, `run_completed`, or `run_failed`;
- the `agent`, its delegation `depth` and `chain`, and `to_agent`;
- `tool_name` and `tool_args`;
- `detail` and `outcome`: the tool result, the teammate's answer, the decision, or the error.

Credentials are redacted before writing. Model token counts are recorded for each agent and each run.

### Problem 5 · Safety guardrails for real-world use

- **Human approval before payments.** Agents can only *propose* payments; every proposed action is fixed to `requires_human_approval: true` and `pending_approval`. The only write tool at this stage, `record_approved_payment`, is never given to an agent (Problem 7 added two more write tools, also withheld from agents); the backend also blocks any agent call to it, and the tool itself rejects blank or AI-agent approvers. A real deployment would add authenticated approvers, role-based limits (for example, two approvers above a dollar threshold), and an approval log tied to user accounts.
- **No negative cash.** `preview_payment_plan` checks a running balance across several payments, and `record_approved_payment` does the balance check and deduction in one SQL statement inside a locked transaction, so even simultaneous approvals cannot overdraw. Amounts always come from the database, never from a caller, and an invoice cannot be paid twice. A real system would also reconcile against the bank and alert on low balances.
- **Protecting customer information.** Customer Service is told to keep internal data (invoices, cash, margins) out of customer messages, and agents see only the tools their role needs. The audit trail stores requester names and order details, so in production it would need access controls, a retention policy, and redaction of personal data beyond credentials.
- **No unauthorized communications.** No tool can email, text, or contact anyone. Every message is a `DraftMessage` with `status: "draft"`, and the prompts forbid saying a message was sent. A real system would send only after a human approves a draft, from an outbox that is logged.
- **Cost and loop control.** Each ticket has 12 delegations at most, chains at most 3 hops deep, and no delegating to yourself or to anyone waiting upstream. All agents on a ticket also share one budget of 60 model requests and 80 tool calls, and each response is capped at 4,000 output tokens. In testing, a ticket used 19–22 requests and about 48k–57k input tokens. Production would add per-day spending caps, alerts, and timeouts per run.
- **Model control.** Only `gpt-6-luna` is configured. Any response from a different model, such as a silent gateway fallback, stops the run.

## Problem 7: FastAPI backend

`backend/main.py` holds the routes and `backend/service.py` holds the logic behind them. Start the server from `backend/` with `uvicorn main:app --reload --port 8000` (inside the project's `.venv`). It serves http://localhost:8000, with interactive docs at `/docs`. Every response is JSON, and every error has the same shape: `{"error": {"code", "message", "details"}}`.

### Problem 7 · Routes

- **GET `/api/health`**: Confirms the backend is up and connected to the MCP server; lists the MCP tools, the model (`gpt-6-luna`), the shop date, and active runs.
- **GET `/api/tickets`**: Every ticket with its database status (`open`/`resolved`), its latest agent run and decision, whether a run is in progress, and its pending approval ids.
- **GET `/api/tickets/{ticket_id}`**: One ticket with all of its runs and proposed actions. `404 ticket_not_found` if it doesn't exist.
- **POST `/api/tickets/{ticket_id}/run`**: Starts the Problem 5 agent team on the ticket (Boss coordinates and delegates) and returns `202` with a `run_id` right away. `404` for an unknown ticket, `409 run_in_progress` if that ticket is already running, and `409 ticket_not_open` if it is already resolved.
- **GET `/api/runs`**: Every run, newest first: `running`, `completed`, `failed`, or `interrupted`, with its decision.
- **GET `/api/runs/{run_id}`**: One run: its status, the Boss's full resolution, any error, the actions it proposed, and `contributions`, a per-agent breakdown taken from the audit trail (who asked it, tools it used, who it delegated to, its own summary, drafts).
- **GET `/api/activity`**: Agent activity read straight from `output/audit_trail.json`: who worked, which tools they called and what came back, delegations, and decisions. Filter with `?ticket_id=` or `?run_id=`. To see new steps as they happen, poll with `?after=<next_cursor>`.
- **GET `/api/approvals`**: Actions the agents proposed, with their review status (`pending`, `paid`, `approved`, `rejected`, `failed`, `stale`, `superseded`, `invalid`). Filter with `?status=` or `?ticket_id=`.
- **GET `/api/approvals/{proposal_id}`**: One proposal, plus what the database showed when it was proposed (amount, payee, due date, whether it was payable).
- **POST `/api/approvals/{proposal_id}/approve`**: Body `{"approved_by": "<name>"}`. A human approves. For a payment, the backend re-checks through MCP that it is unpaid, the amount is unchanged, and cash covers it, then calls `record_approved_payment`. Errors: `409 already_paid`, `insufficient_cash`, `amount_changed`, `stale_proposal`, or `invalid_proposal`; `422` if the approver is blank or an agent's name.
- **POST `/api/approvals/{proposal_id}/reject`**: Body `{"rejected_by": "<name>", "reason": "..."}`. A human rejects; nothing in the database changes. `409 already_decided` if it was already decided.
- **GET `/api/cash`**: The current checking balance from `cash_accounts`. It changes only when an approved payment is recorded. Also returns `proposed_payments`: every pending payment proposal previewed through MCP (`preview_payment_plan`), each on its own and all together, so the dashboard can show actual cash next to what it would be if everything pending were approved. Nothing is paid.
- **POST `/api/database/reset`**: Body `{"confirm": "RESET", "requested_by": "<name>"}`. Restores `data/campus_customs_new.db` from the original. Refused with `409 run_in_progress` during an agent run and `409 database_busy` during another write; it waits for any approval in progress. The audit trail is kept.

### Problem 7 · How the rules are enforced

- **MCP is still the only door to the database.** The backend calls MCP tools for every read and write, including tickets, cash, previews, payments, status, and reset, and imports nothing that touches SQLite. Problem 7 added three MCP tools for that purpose, none of which an agent can call:
  - `list_tickets` (read `tickets`);
  - `update_ticket_status` (write `tickets.status`; used only when the Boss decides `resolved`);
  - `reset_working_database_to_original` (restores every table in one locked transaction; requires `confirm="RESET"`).
- **No money moves without a human.** Agents can only propose. A proposal is approvable only if an agent run actually produced it: the backend records it in the audit trail and checks its amount against the database. Nothing can be approved by naming an arbitrary amount or target. Approving re-verifies everything, and `record_approved_payment` re-checks the balance atomically, so cash can't go negative even under concurrent approvals.
- **No duplicates.**
  - A paid invoice can't be paid again.
  - A rent installment can't be paid twice, because the lease's due date has moved on.
  - A proposal from before a reset is `stale`, and one replaced by a newer run of the same ticket is `superseded`; neither can be approved.
- **History is never erased.** Proposals, approvals, rejections, payments, failures, status changes, and resets are appended to `output/audit_trail.json`, so pending approvals survive a server restart.

## Problem 8: React dashboard

`frontend/` is a React 19 + TypeScript app built with Vite (`npm run dev`, http://localhost:5173). It talks only to the FastAPI backend at http://localhost:8000; it never touches the database and has no mock data. The design rationale is in `output/design.md`.

### Problem 8 · Features

- **Header**: Shop date, backend connection and model, the **actual checking balance** (pulses when it changes), and a "Reset shop data" button.
- **"Today at the desk"**: A one-line, data-driven headline (decisions waiting, runs in progress, tickets resolved) and the five-agent team strip.
- **Ticket board**: One card per ticket with ID, subject, requester, notes, SKU/size/qty/lease/invoice, a truthful status (Resolved only when `tickets.status` is resolved; otherwise awaiting approval, blocked, needs information, run failed, or not started, always followed by "Still open"), and **Start the team / Run the team again**.
- **Team at work**: For the selected ticket and run: a five-seat roster (involved / working now / not involved), **"How the work moved"** handoff chips, a live step-by-step timeline from the audit trail (handoffs with the quoted request, answers, tool calls in plain words with the returned facts, decisions, approvals), and, when finished, the outcome: decision, Boss summary, "Who did what" per agent, drafts stamped **Draft · not sent**, outstanding outside dependencies, next steps, open questions, and the evidence.
- **Your decisions**: **Checking · actual** (from `cash_accounts`) beside proposed payments previewed through MCP ("Proposed, not approved" and "If every proposal were approved"), the approval queue (purpose, payee, amount, and checking before → after), Review & approve (requires a name; optional note for the agents), Decline (name and reason), and "Recently decided" (excluding anything a reset undid).
- **Safety in the UI**: Approve/reset need a typed name; reset also needs `RESET` and is disabled during runs; backend errors become plain-language notices; an offline banner retries automatically.

## Problem 9: Clean run results and final system reference

### Problem 9 · What happened in the clean run

The working database was reset to the original (audit record **#335**, 2026-10-08 21:42:49 UTC; verified identical, original checksum unchanged). Every audit record after #335 is the graded run. An earlier attempt (records 174–334) was undone by that reset because browser automation garbled the approver's name; it stays in the audit trail as history.

Each ticket was started from the dashboard and taken to a final decision by the agents. Between runs, the human approved requests in the dashboard. All three tickets ended **resolved** (set by the backend only after the Boss decided `resolved`):

- **101 Bulldog tee**
  - Runs: 4 (awaiting approval ×3, then resolved)
  - Human decisions (all by Charlotte Simonds): Pay invoice 501 ($840, recorded as payment 2); approve restock of 1 size-S tee (decision only)
  - Cash: −$840.00
  - Outside dependencies still open: Send vendor and customer drafts; vendor price and terms; ordering and delivery
- **102 Rent due**
  - Runs: 4 (awaiting approval, failed on a network error, needs information, resolved)
  - Human decisions (all by Charlotte Simonds): Pay rent, lease 1, installment due 2026-09-02 ($2,400, recorded as payment 1)
  - Cash: −$2,400.00
  - Outside dependencies still open: Landlord's confirmation of receipt
- **103 Bulk hoodies**
  - Runs: 3 (awaiting approval ×2, then resolved)
  - Human decisions (all by Charlotte Simonds): Approve 10% discount ($52.20/hoodie) twice: first for 20 with a note limiting it to the 8 in stock, then for up to 8 (decisions only)
  - Cash: $0.00
  - Outside dependencies still open: Club's choice of 8 now or wait; no restock of the 12 committed

**Cash:** $3,400.00 − $2,400.00 − $840.00 = **$160.00**, equal to `cash_accounts.checking`. `payments` holds exactly 2 rows, and no payment was recorded twice. The full itemized reconciliation is on the Cash tab of `output/desk_tickets.html`, the per-ticket records are in `output/resolved_tickets.json`, and dashboard screenshots are in `output/resolved_board.html`.

### Problem 9 · Operational resolution

**Definition.** Operational resolution means the agents completed all of the actionable work available to them inside the simulation: the necessary human approvals were obtained and recorded, the decisions were documented, and the communications were prepared as drafts. The simulation cannot send messages, place purchase orders with vendors, receive deliveries, or record a customer's reply (the assignment prohibits contacting real customers or vendors), so those external steps are listed as outstanding. This is a limitation of the simulation, not work the agents left undone, and nothing here implies that a product was delivered, a purchase order was executed, or an offer was accepted.

**How the implementation enforces it.**
- `tickets.status` can only be `open` or `resolved` (`update_ticket_status`). The backend sets `resolved` only after the Boss decides `resolved` in a run.
- The Boss's instructions define `resolved` as: every needed payment appears in payment history, every needed human decision is recorded, the reply is drafted, and nothing awaits approval. Steps outside the simulation go in `outstanding_dependencies` instead of being treated as done.
- No tool sends a message or records a purchase order, so the agents cannot claim either.

- **101**
  - Approved by a human: Invoice 501 payment, $840 (payment 2); restock of 1 size-S tee (decision only; no purchase order record)
  - Accomplished by the agents: Verified stockout, vendor block and shared cash; prepared both approvals; drafted the vendor order inquiry and the customer reply
  - External steps outstanding (limitation of the simulation): Send the drafts; vendor confirms price, terms and delivery; order placed and tee delivered
- **102**
  - Approved by a human: Rent payment, $2,400 for the 2026-09-02 installment (payment 1)
  - Accomplished by the agents: Verified lease, payment status and cash; prepared the payment; confirmed the installment covered; drafted a receipt-confirmation note
  - External steps outstanding (limitation of the simulation): Send the note; landlord confirms receipt
- **103**
  - Approved by a human: 10% discount, $52.20/hoodie, for the 8 in stock with the option to wait (decisions only)
  - Accomplished by the agents: Verified stock (8 of 20), margins ($30.20, 57.85%) and shared cash; drafted the offer
  - External steps outstanding (limitation of the simulation): Send the offer; the club chooses; any restock of the 12 needs a confirmed price, funds and approval

Nothing in this system indicates that a product was delivered, a purchase order was executed, or an offer was accepted.

### Problem 9 · Changes made during Problem 9 (and why)

- **Runs receive other tickets' pending payment requests and the human decisions already recorded on the ticket (backend `_shop_context`, logged in each `run_started` record)**
  - Reason: Accounting must weigh shared cash; agents could not see approvals that live only in the audit trail
  - First used by: All clean-run runs
- **Boss `resolved` definition, the `outstanding_dependencies` field, and notes attached to approvals**
  - Reason: Physical completion is impossible by design; the human's conditions (offer 8, don't assume acceptance) had to reach the agents
  - First used by: All clean-run runs
- **Context and approvals limited to events after the last reset**
  - Reason: Pre-reset approvals no longer apply to the restored database
  - First used by: All clean-run runs
- **`get_lease_rent_status` returns recorded rent payments and explains `next_due`; context shows the installment date**
  - Reason: Run 85318a203180 could not tell which installment payment 1 covered
  - First used by: Ticket 102 run 9030e8ba7b2e onward
- **Rule: no re-requesting approved actions; ordering is outside the system, so draft the vendor message**
  - Reason: Run 8c75cb6fad82 asked again to approve the already-approved order
  - First used by: Ticket 101 final run f6d2e5216407
- **Dashboard: outcome wording for resolved tickets now names the outside dependencies; the ribbon no longer covers labels**
  - Reason: The old line ("nothing left waiting") contradicted the dependencies listed
  - First used by: Screenshots in `resolved_board.html`

### Problem 9 · Database (`data/campus_customs_new.db`, a working copy of the untouched `data/campus_customs.db`)

- **desk**
  - Fields: date_today, notes
  - Why the agents need it: The shop's "today" for every due/overdue judgment.
- **tickets**
  - Fields: id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at
  - Why the agents need it: The work queue; its ids route each ticket to the right records; `status` is set to resolved only after the Boss decides so.
- **inventory**
  - Fields: sku, name, size, qty, location
  - Why the agents need it: Stock by SKU and size, and shortfalls.
- **pricing**
  - Fields: sku, unit_cost, list_price
  - Why the agents need it: Margins and discount checks; `unit_cost` is an accounting cost, not a vendor quote.
- **vendors**
  - Fields: id, name, specialty, lead_days
  - Why the agents need it: Who can restock what (matched by specialty) and how long delivery takes.
- **leases**
  - Fields: id, space_name, landlord, monthly_rent, next_due, notes
  - Why the agents need it: Rent amount and the next unpaid installment.
- **cash_accounts**
  - Fields: name, balance, date
  - Why the agents need it: The checking balance; it can never go negative and only falls when a human-approved payment is recorded.
- **payments**
  - Fields: id, kind, ref_id, amount, account, paid_at, approved_by
  - Why the agents need it: The record of completed, human-approved payments.
- **invoices**
  - Fields: id, vendor_id, amount, due_date, status, description
  - Why the agents need it: What the shop owes; an unpaid invoice blocks that vendor from shipping.

### Problem 9 · MCP tools (14, FastMCP server in `mcp_server/`, the only route to the database)

- **`get_ticket`**
  - Tables: tickets, desk
  - Business function: Read one ticket and the shop date
  - Who can call it: All five agents; backend
- **`list_open_tickets`**
  - Tables: tickets, desk
  - Business function: List open tickets
  - Who can call it: Boss
- **`list_tickets`**
  - Tables: tickets, desk
  - Business function: List all tickets with status
  - Who can call it: Backend
- **`get_product_stock_and_pricing`**
  - Tables: inventory, pricing
  - Business function: Stock by size, unit cost, list price
  - Who can call it: Inventory, Accounting, Customer Service
- **`evaluate_price_override`**
  - Tables: pricing
  - Business function: Revenue and margin at list vs. a proposed price; flags at/below cost
  - Who can call it: Accounting
- **`list_vendors`**
  - Tables: vendors, invoices, desk
  - Business function: Specialty, lead time, can-ship, earliest arrival
  - Who can call it: Inventory, Accounting
- **`check_vendor_invoice_status`**
  - Tables: invoices, vendors, desk
  - Business function: A vendor's invoices, days overdue, can-ship
  - Who can call it: Inventory, Accounting
- **`get_lease_rent_status`**
  - Tables: leases, payments, desk
  - Business function: Rent, next unpaid installment, days until due, recorded rent payments
  - Who can call it: Accounting, Facilities
- **`get_cash_balance`**
  - Tables: cash_accounts, desk
  - Business function: Current balance
  - Who can call it: Accounting
- **`get_payment_history`**
  - Tables: payments, desk
  - Business function: Whether something is already paid
  - Who can call it: Accounting, Facilities
- **`preview_payment_plan`**
  - Tables: invoices, vendors, leases, cash_accounts, desk
  - Business function: Running balance across several payments; pays nothing
  - Who can call it: Accounting, Facilities; backend
- **`record_approved_payment`**
  - Tables: cash_accounts, payments, invoices, leases, desk
  - Business function: Make a human-approved payment in one locked transaction (rejects overdraft, double payment, blank or agent approvers)
  - Who can call it: Backend approval route only
- **`update_ticket_status`**
  - Tables: tickets
  - Business function: Set open/resolved after the Boss decides
  - Who can call it: Backend only
- **`reset_working_database_to_original`**
  - Tables: all tables
  - Business function: Restore the working copy from the original (requires `confirm="RESET"`; refuses if busy)
  - Who can call it: Backend reset route only

### Problem 9 · Agents and delegation (PydanticAI, `backend/team.py`, prompts in `backend/prompts/`)

- **Boss**
  - Responsibility: Reads the ticket, delegates, checks answers against each other, decides `resolved` / `awaiting_approval` / `blocked` / `needs_more_information`, and lists outside dependencies
  - MCP tools: get_ticket, list_open_tickets
- **Inventory**
  - Responsibility: Stock and shortfalls, vendor by specialty, can-ship check, earliest arrival; drafts vendor order messages
  - MCP tools: get_ticket, get_product_stock_and_pricing, list_vendors, check_vendor_invoice_status
- **Accounting**
  - Responsibility: Cash, invoices, payment history, combined payment previews, margins and discounts; proposes payments and purchase orders for approval
  - MCP tools: get_ticket, get_cash_balance, get_payment_history, preview_payment_plan, check_vendor_invoice_status, list_vendors, get_product_stock_and_pricing, evaluate_price_override, get_lease_rent_status
- **Facilities**
  - Responsibility: Lease and rent timing, rent payment preparation, landlord drafts
  - MCP tools: get_ticket, get_lease_rent_status, get_payment_history, preview_payment_plan
- **Customer Service**
  - Responsibility: Drafts replies from verified facts only; never sends
  - MCP tools: get_ticket, get_product_stock_and_pricing

**Full connectivity:** every agent has `ask_teammate` and can ask any other agent directly. In the clean run this produced specialist-to-specialist handoffs such as Inventory → Accounting, Facilities → Accounting, Accounting → Inventory, and Customer Service → Inventory/Accounting/Facilities. **Guards:**
- No asking yourself.
- No asking an agent already waiting upstream (refused, and the refusal is logged).
- At most 3 levels deep and 12 delegations per ticket.
- Teammates' earlier answers are shared, to avoid repeat questions.

All agents run only `gpt-6-luna` through Portkey, and any response served by another model stops the run.

### Problem 9 · Backend routes (`backend/main.py`, http://localhost:8000)

- **GET `/api/health`**: Status, model, MCP tools, shop date, active runs
- **GET `/api/tickets`**: All tickets with database status, latest run (decision, outstanding dependencies), running flag, pending approvals
- **GET `/api/tickets/{ticket_id}`**: One ticket with all runs and proposals
- **POST `/api/tickets/{ticket_id}/run`**: Start the team on an open ticket (202 with `run_id`); 404/409 errors
- **GET `/api/runs`**: All runs, newest first
- **GET `/api/runs/{run_id}`**: Run status, Boss resolution, proposals, per-agent contributions
- **GET `/api/activity`**: Audit records; `?after=` cursor for live polling; filters by ticket or run
- **GET `/api/approvals`**: Proposals with review status (pending, paid, approved, rejected, failed, stale, superseded, invalid) and the before/after-reset flag
- **GET `/api/approvals/{proposal_id}`**: One proposal and what the database showed when it was proposed
- **POST `/api/approvals/{proposal_id}/approve`**: `{approved_by, note?}`; payments are re-verified, then recorded via MCP
- **POST `/api/approvals/{proposal_id}/reject`**: `{rejected_by, reason?}`; records the decision only
- **GET `/api/cash`**: Checking balance from `cash_accounts`, plus pending payment proposals previewed via MCP
- **POST `/api/database/reset`**: `{confirm: "RESET", requested_by}`; refused during runs or concurrent writes; audit trail kept

### Problem 9 · Safety rules (as implemented)

- **Human approval for payments.**
  - Agents can only propose. `record_approved_payment` is withheld from every agent and also blocked by the backend.
  - The approval route only accepts proposals an agent run actually produced. It requires a named human, refusing blank or agent names, and re-verifies amount, payee, unpaid status, and installment date through MCP before paying.
- **No negative balances.**
  - The balance check and the deduction happen in one SQL statement inside a locked transaction.
  - Previews show the running balance across all pending payments.
  - Lowest balance in the clean run: $160.00.
- **No duplicate payments.**
  - A paid invoice cannot be paid again, and rent advances `next_due` so the same installment cannot be paid twice.
  - Proposals from before a reset or from older runs cannot be approved.
- **No real communications.**
  - No tool sends anything. Every message is a `DraftMessage` with status `draft`, shown as "Draft · not sent".
  - Purchase orders are recorded only as approved decisions.
- **Database integrity.**
  - The MCP server is the only database access; the backend has no SQLite code.
  - The original database is only ever read.
  - Reset runs in one locked transaction and gives up rather than interrupting a writer.
  - Every step, proposal, decision, payment, and reset is appended to `output/audit_trail.json`, with credentials redacted; nothing is overwritten.
- **Token and loop control.**
  - Per ticket: 60 model requests, 80 tool calls, 12 delegations, and a depth of 3.
  - Each response is capped at 4,000 output tokens with a 120 s timeout.
  - In the clean run a single run used 9–30 requests and 27.5k–97.2k input tokens.
- **Credentials.** `PORTKEY_API_KEY` is read from `.env` only. It does not appear in code, the audit trail, or any output file.
