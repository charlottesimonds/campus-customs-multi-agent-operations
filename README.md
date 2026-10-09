# Campus Customs Multi-Agent Operations

Campus Customs is a fictional campus apparel shop. This project is a team of five AI agents that works the shop's open tickets (a customer order, a rent notice, and a bulk-discount request) under human supervision:

- **MCP server** (`mcp_server/`): the only way to read or change shop data.
- **FastAPI backend** (`backend/`): runs the agent team and handles human approvals.
- **React dashboard** (`frontend/`): lets a person watch the agents, approve payments, and see the checking balance.

## How it fits together

- **The MCP server** (FastMCP, `mcp_server/`) exposes 14 tools over the SQLite working database `data/campus_customs_new.db`: stock and pricing, vendors and invoices, the lease, cash, payment previews, and (for human-approved actions only) recording payments, setting ticket status, and resetting the database. No other component touches the database.
- **The agent team** (PydanticAI, `backend/team.py`, prompts in `backend/prompts/`) has five agents. Every agent can ask any other agent for help through an `ask_teammate` tool; work does not have to go through the Boss. Each agent may call only the MCP tools its role needs.
  - **Boss**: reads each ticket, delegates, checks the answers against each other, and makes the final decision.
  - **Inventory**: stock by SKU and size, shortages, which vendor can restock, lead times, and whether a vendor may ship.
  - **Accounting**: cash, invoices, payment history, margins, and discounts. It proposes payments and purchases for human approval and can never make them.
  - **Facilities**: the lease, rent amounts and due dates, and the landlord.
  - **Customer Service**: drafts replies to customers and other requesters. Drafts are never sent.
- **The backend** (FastAPI, `backend/main.py`) starts runs, streams activity from `output/audit_trail.json`, holds proposed actions for human review, records approved payments through MCP, and reports the checking balance.
- **The dashboard** (React + Vite + TypeScript, `frontend/`) shows the tickets, the agents at work, the approval queue, and the actual checking balance alongside proposed payments.
- **The model**: every agent uses only `gpt-6-luna` through Portkey (`PORTKEY_API_KEY`). A run stops if a response comes from any other model.

**Business rules the system enforces:**
- The shop's "today" is `desk.date_today` (2026-08-31).
- A vendor with an unpaid invoice cannot ship.
- Every payment needs a named human's approval.
- Cash can never go negative, and a payment cannot be recorded twice.
- Nothing is ever emailed or sent: messages are drafts.

## What is in this repository

- `data/campus_customs.db`: the original data pack. It is never modified.
- `data/campus_customs_new.db`: the working database. **As submitted, it preserves the completed assignment run** (see "The two database states" below).
- `mcp_server/`: the MCP server (`server.py`, `db.py`, `reset_db.py`, `tools/`) and its README.
- `backend/`: `main.py` (API routes), `service.py` (runs, approvals, cash, reset), `team.py` (the five agents and delegation), `models.py`, `config.py`, `audit.py`, and `prompts/` with one prompt per agent.
- `frontend/`: the React dashboard.
- `output/`: the assignment deliverables.
  - `harness.md`: full system documentation; the Problem 9 section is the current reference.
  - `mcp_smoke.json`: MCP tool test results.
  - `desk_tickets.html`: Expected and Actual results per ticket, the Cash reconciliation, and the Reflection.
  - `design.md`: dashboard design rationale.
  - `resolved_tickets.json`: final outcome, agent contributions, and approvals for each ticket.
  - `resolved_board.html`: screenshots of the dashboard showing the three resolved tickets.
  - `audit_trail.json`: every agent step, tool call, delegation, approval, and reset.
  - `github_url.txt`: this repository's URL.
- `AI_prompts.md`: the prompts used to build the project.
- `.mcp.json`: lets Claude Code connect to the MCP server.
- `.env.example`: the template for your `.env`.

## Requirements

- Python 3 (developed and tested with Python 3.13).
- Node.js 20.19+ or 22.12+ (Vite's requirement; tested with Node 24) and npm.
- A Portkey API key with access to `gpt-6-luna`.

The commands below are for macOS or Linux. On Windows, activate the virtual environment with `.venv\Scripts\activate`; `.mcp.json` is written for macOS and Linux paths.

## Setup

1. **Clone the repository:**
   ```
   git clone https://github.com/charlottesimonds/campus-customs-multi-agent-operations.git
   cd campus-customs-multi-agent-operations
   ```
2. **Install the Python dependencies** into a virtual environment named `.venv` at the project root (`.mcp.json` expects this name):
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Install the frontend dependencies:**
   ```
   cd frontend
   npm install
   cd ..
   ```
4. **Configure your API key:** create `.env` from the template and replace the placeholder with your Portkey key.
   ```
   cp .env.example .env
   ```
   `.env` is ignored by Git, and the backend finds it automatically.

## Running the application

Use three terminals. Each starts from the project root with the virtual environment active (`source .venv/bin/activate`).

1. **MCP server (optional to start yourself):**
   ```
   python -m mcp_server.server
   ```
   It speaks MCP over stdio and waits for a client. You do not need to start it for the dashboard: the backend launches its own copy automatically, and Claude Code launches one from `.mcp.json`. Run it directly only to inspect it or connect another MCP client.
2. **FastAPI backend:**
   ```
   cd backend
   uvicorn main:app --reload --port 8000
   ```
   It serves http://localhost:8000; the interactive API docs are at http://localhost:8000/docs. The bare address shows "Not Found" because every route is under `/api/`.
3. **React dashboard:**
   ```
   cd frontend
   npm run dev
   ```
4. **Open http://localhost:5173** in your browser. The header should say "Connected · gpt-6-luna" and show the checking balance.

## Using the dashboard

1. **Pick a ticket.** Click ticket 101, 102, or 103 on the ticket board.
2. **Run the team.** Click **Start the team** (or **Run the team again**). The run takes about a minute. "Team at work" shows:
   - which agents are working, and how the work moved between them;
   - every step as it happens: handoffs with the actual question asked, MCP tool calls with what they returned, and answers.
3. **Review the outcome.** When the run finishes you see:
   - the Boss's decision and summary;
   - what each agent contributed;
   - drafted messages, stamped "Draft · not sent";
   - outside dependencies, next steps, and the evidence.
4. **Review approval requests.** Anything that needs a human appears under **Needs your decision**. Payment cards show the amount, the payee, and the checking balance before and after. **Review & approve** asks for your name (and an optional note for the agents); **Decline** records a refusal. The backend checks again that the payment is unpaid, the amount is unchanged, and cash covers it before recording it.
5. **Re-run after deciding.** Run the ticket again so the agents see the new state. The Boss marks a ticket resolved only when everything within the shop's control is done.

**The checking balance** (header and right column) comes from `cash_accounts`. It changes only when an approved payment is recorded. Proposed payments are shown separately and do not move money.

## The two database states

- **As submitted**, `data/campus_customs_new.db` preserves the completed assignment run:
  - Tickets 101, 102, and 103 are resolved.
  - Two human-approved payments are recorded: rent $2,400 for lease 1, and vendor invoice 501, $840.
  - Checking is $160.00 ($3,400.00 − $2,400.00 − $840.00).
  - The evidence for this run is in `output/` and `output/audit_trail.json`.
- **To reproduce the workflow from the beginning in your own clone**, restore the working database from the original before running the three tickets. Choose one way:
  - In the dashboard, click **Reset shop data**, enter your name, and type `RESET`.
  - With the backend stopped, from the project root:
    ```
    python -m mcp_server.reset_db
    ```
  - With all servers stopped, copy the file:
    ```
    cp data/campus_customs.db data/campus_customs_new.db
    ```

  The original `data/campus_customs.db` is never changed. New runs append to `output/audit_trail.json`, so a fresh run in your clone adds to the submitted history rather than replacing it.

## What "resolved" means

A ticket is resolved when the agents have completed all the actionable work available to them inside the simulation:
- the necessary human approvals were obtained and recorded;
- decisions were documented;
- communications were prepared as drafts.

The simulation cannot send messages, place purchase orders with vendors, receive deliveries, or record a customer's reply; the assignment prohibits contacting real customers or vendors. So a resolved ticket does **not** mean an order was delivered or a message was sent. Those external steps are listed as outstanding for each ticket in the dashboard, `output/resolved_tickets.json`, and `output/desk_tickets.html`.

## Results of the submitted run

- **Ticket 101 (Bulldog tee):**
  - Invoice 501 was paid ($840), clearing the vendor to ship.
  - Restocking one size-S tee was approved as a decision.
  - Order and reply messages were drafted.
- **Ticket 102 (rent):**
  - The $2,400 rent for the 2026-09-02 installment was paid.
  - A receipt-confirmation note to the landlord was drafted.
- **Ticket 103 (bulk hoodies):**
  - A 10% discount ($52.20 per hoodie) was approved for the 8 in stock.
  - An offer giving the club the option to wait for the other 12 was drafted.
  - No cash moved.

The itemized reconciliation is on the Cash tab of `output/desk_tickets.html`. The full system reference is `output/harness.md`.
