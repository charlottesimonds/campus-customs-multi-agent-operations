# AI Prompts



# Problem 2
Prompt 1: Yay let's do problem 2. I need to understand the Campus Customs database before we start building the agents and tools that will use it. Please open data/campus_customs.db and inspect every table, including the fields/columns in each table and the data they contain. I especially want to understand how the tables relate to one another.
Then look closely at the three currently open tickets and trace each ticket to any relevant information in the other tables so I understand what data would be needed to resolve each one.
Before making any changes, create a copy of the original database called data/campus_customs_new.db. We will use this new database as the working copy in later problems, while data/campus_customs.db should remain completely unchanged.
For now, I mainly want you to help me understand the database structure, the three open tickets, and how their information connects across the different tables.

I also need to start an output/harness.md file that documents what we learned about its structure.
For every table in the Campus Customs database, please add the table name, list all of the fields/columns in that table, and write one short sentence explaining why that table is relevant to the agents we will eventually build.
Keep this organized and concise because output/harness.md will be a running documentation file that we continue adding to in later problems. Do not replace or redesign the database; this step is just documenting our understanding of the existing tables and how they will matter to the agent system.

# Problem 3
Promt 1: Now for Problem 3 you need to build the MCP server that will provide the tools used by all of the agents in the Campus Customs system.
Please create the MCP server inside the mcp_server/ directory using FastMCP. It should connect to our working database, data/campus_customs_new.db, rather than the untouched original database.
Based on the database structure and the three open tickets we studied in Problem 2, create three MCP tools that we know the agents will need to work on those tickets. Choose the tools based on the actual information and needs you found in the database, and give each tool a clear, descriptive name so its purpose will be obvious to an agent.
The tools should retrieve or work with real information from campus_customs_new.db. They should never make up information or fill in missing data with assumptions. if something is not in the database, it should not be invented.
We will add more tools to this MCP server in later problems, so please structure it in a way that will be easy to extend. For this problem, I only need the server and these three tools written; I do not need to connect or run the MCP server yet. 

I also need you to document the three MCP tools we just created and add that documentation to the existing output/harness.md file.
For each of the three tools, please include:
- The name of the MCP tool
- The specific database table or tables it reads
- Which open ticket it helps resolve: 101, 102, or 103
- One specific sentence explaining why the information returned by that tool is needed to resolve that particular ticket. Please tie the explanation directly to the actual issue in the ticket rather than giving a generic description like “this tool reads inventory.”
Please preserve the material already in output/harness.md from Problem 2 and add this as a new section rather than replacing the existing documentation.
Also create a short mcp_server/README.md. Explain what the MCP server is for, state that it uses the working database data/campus_customs_new.db, and briefly describe each of the three MCP tools we created.
Keep both pieces of documentation concise and consistent with the actual MCP server implementation and database we have already built. Thank youuuu 



# Problem 4
Now that we have built the MCP server and its three tools, I need to connect that server to Claude Code so that you can access and call those tools directly within this project. Can you walk me through how to do that? 

Please configure the existing MCP server as a local server for this project and save the connection settings in a .mcp.json file at the project root, or use the appropriate configuration format if Claude Code requires something different.

Make sure the configuration points to the MCP server we created in Problem 3 and uses our working database, data/campus_customs_new.db, rather than the original database.

For now, I want to establish the connection so Claude Code can recognize and use the three tools. Please preserve the existing implementation and avoid making unnecessary changes to the server or database.

Prompt 2: 
The thing is that i imagine graders will need to run this on their own computers. do you recommend i stop working in vs code and instead use the claude desktop application by logging into this account? what do you think i should do to streamline this process, I just use VS code bcause i prefer the interface

Reason for Prompt 2: I just wanted to make sure that before we build anything, its replicable and wouldnt be inhibited by the fact that i prefer not to use Claude Code natiev and instead run everything through VS code 



# Problem 5
Prompt 1: Great, Let's do Problem 5. So now you need to build the actual multi-agent team for Campus Customs using PydanticAI, building on the MCP server and database we have already set up.

Please create five distinct agents: Boss, Inventory, Accounting, Facilities, and Customer Service. Each should have a clearly defined role, its own detailed system prompt, and the ability to delegate tasks to any of the other agents when their expertise is needed. I want full connectivity between the agents!!!!!! rather than a system where every interaction must go through the Boss.

Please organize the implementation under backend/, with a separate prompt file for each agent in backend/prompts/ and the necessary data types and shared models in backend/models.py. The prompts should be written in clear, specific language that reflects how each agent would actually operate in our shop.

Make sure each agent understands the business rules relevant to its responsibilities. For example, Inventory needs to account for stock availability, vendor lead times, and unpaid invoices before recommending restocking. Accounting needs to verify available cash, monitor invoices and margins, and require human approval before any payments. Facilities should handle rent and lease obligations, while Customer Service should draft responses without sending them. Boss should evaluate incoming tickets, coordinate the team, and make final decisions while respecting approval requirements.

Please implement the agent loops and delegation logic so agents can exchange information and collaborate on tickets without getting stuck in infinite delegation cycles.

All five agents must use only gpt-6-luna through Portkey, authenticated with PORTKEY_API_KEY. Do not introduce any other model.

Please preserve the existing MCP server and database structure and make this implementation compatible with the tools we have already created. I want the system to be extensible as we continue through the assignment and build on it/ iterate 

now also as part of problem 5, now that we have implemented the five PydanticAI agents, I need to expand our MCP server to ensure the agents have all the tools necessary to investigate and resolve the three open Campus Customs tickets. that seems like something you have already kindly alerted me to in your first pass. I need you to : 

1. Expand the MCP tools

Please review tickets 101, 102, and 103, the existing MCP tools, and the responsibilities of each agent. Identify any additional tools the agents need to investigate and resolve these tickets, and implement them within our existing MCP server.

Make sure the tools use actual information from data/campus_customs_new.db and follow the shop's business rules, including vendor restrictions, cash limitations, and human approval requirements for payments.

2. Enforce MCP as the only database access point

This is a particularly important architectural requirement: the MCP server must be the single source of truth for all shop data accessed by the agents.

Every agent must retrieve shop information and perform database-related operations exclusively through MCP tools connected to data/campus_customs_new.db.

The agents should never directly query SQLite, open database connections, or use a separate database-access layer that bypasses MCP.

If an agent needs information or functionality that the existing MCP tools cannot provide, please implement an additional MCP tool rather than creating a workaround in the backend.

Please review the agent implementation to verify that all database reads and writes follow this architecture. The backend should handle agent reasoning, delegation, and coordination, while the MCP server handles database access and operations.

3. Implement an audit trail

I also need the agents to maintain an audit trail so we can understand and review what happened during each run.

Please configure the agent loops to append records to output/audit_trail.json. For each agent-loop step, record enough information to reconstruct what happened, including the agent involved, the ticket being worked on, the action taken, any MCP tool calls or delegations, and the outcome.

The audit trail should accumulate records across runs rather than being overwritten. Please also ensure it does not expose sensitive credentials.

4. Update the harness documentation

Please update our existing output/harness.md file to include:

All five agents and their individual responsibilities.

A complete list of every MCP tool, including the tools created in earlier problems and the ones added now.

The specific database table or tables each tool accesses.

A short safety section explaining the guardrails that would be necessary if this system were used in a real business.

The safety section should address human approval before payments, preventing negative cash balances, protecting customer information, preventing unauthorized communications with customers or vendors, and controlling token consumption and agent delegation to avoid excessive costs or infinite loops.

5. Update the MCP server README

Please update mcp_server/README.md so that it accurately reflects the current MCP server implementation and includes all available tools.

6. Verify the implementation

Before finishing, please review the code to confirm that:

All five agents can access the appropriate MCP tools.

No agent bypasses MCP to access the shop database.

The new tools support the actual needs of tickets 101, 102, and 103.

The audit trail appends records rather than replacing previous runs.

The documentation accurately reflects the implementation.

Please preserve all existing functionality and documentation from earlier problems. I want this to build on what we have already created rather than unnecessarily restructure the project.

# Problem 6
Prompt 1: 
Now on to Problem 6. Please summarize tickets 101, 102, and 103 using the information in our database, and remind me of the MCP tools we have implemented so far.

For each ticket, help me understand the central problem, which agents have the relevant expertise, and what decisions will likely need to be made. help me reason through the likely workflow for each ticket so I can decide who Boss should delegate to first, what subsequent delegations make sense, and which tools should be used

Prompt 2: I want to complete Problem 6 by creating a planning dashboard that documents how I expect our multi-agent team to handle each ticket before we actually run the agents.

Please create output/desk_tickets.html as an HTML dashboard with five tabs: Ticket 101, Ticket 102, Ticket 103, Cash, and Reflection.

Each ticket tab should contain an Expected section with my predictions about how the agents should collaborate, and a separate Actual section that we will fill in after running the system. For now, leave all Actual sections empty.

The Cash and Reflection tabs should also remain blank or display a short "Coming later" message because we will complete those in subsequent problems.

Below are my expectations for each ticket, based on what we learned from the database. Please use these as the foundation for the dashboard, keeping the explanations clear, specific, and in my own words.

Ticket 101 Customer order for a Classic Bulldog Tee

I expect Boss to delegate to Inventory first because the central question is whether we have the requested product available. Inventory should use get_product_stock_and_pricing to confirm that the customer needs a size S tee and that we currently have zero units available in that size.

Inventory should then use list_vendors and check_vendor_invoice_status to determine whether the appropriate vendor can restock the item. I expect it to discover that Bulldog Print Co is blocked from shipping because invoice 501 for $840 remains unpaid.

I would also expect Boss to involve Accounting, potentially in parallel with Inventory, because the ticket already references the unpaid invoice. Accounting should use get_payment_history, get_cash_balance, and preview_payment_plan to determine whether the shop can afford to clear the invoice and whether doing so would conflict with other financial obligations.

If Inventory needs clarification about the unpaid invoice, it should be able to delegate directly to Accounting rather than going back through Boss.

Once the stock and payment situation is understood, Boss should involve Customer Service to draft an appropriate response explaining that the requested size is unavailable and restocking depends on resolving the vendor payment issue. The response should not promise a delivery date that has not been confirmed.

I expect the ticket to require human approval before the $840 payment can be made. Until that happens, the ticket should remain awaiting approval rather than being marked fully resolved.

Ticket 102 Upcoming rent payment

I expect Boss to contact Facilities first because this ticket concerns the shop's lease and rent obligations.

Facilities should use get_lease_rent_status to confirm that the $2,400 rent payment for the Chapel Street location is due on September 2, 2026. Since the shop date is August 31, this payment is due in two days rather than already overdue.

Facilities should then coordinate with Accounting to determine whether the rent has already been paid and whether the shop has sufficient funds to cover it.

Accounting should use get_payment_history, get_cash_balance, and preview_payment_plan. Importantly, I would expect Accounting to consider the other outstanding financial obligations rather than evaluating rent in isolation.

The shop has $3,400 in cash. Paying the $2,400 rent and the $840 vendor invoice would leave only $160. I expect Accounting to flag this limited remaining cash to Boss before recommending payments.

Boss should then prepare the rent payment for human approval. No payment should be executed automatically.

I do not expect Inventory to be involved in this ticket because there is no inventory-related issue. Customer Service may not be necessary either, unless a written acknowledgment to the landlord is appropriate.

I expect the ticket to remain awaiting approval until a human authorizes the payment.

Ticket 103 Yale AI Club bulk hoodie order and discount request

I expect Boss to involve Inventory first because the shop needs to determine whether it can fulfill the club's requested quantity before deciding what discount to offer.

Inventory should use get_product_stock_and_pricing to confirm that the club wants 20 medium Basic Hoodies but the shop only has 8 in stock, leaving a shortage of 12.

Inventory should then use list_vendors and check_vendor_invoice_status to investigate restocking options. I expect it to discover that Bulldog Print Co cannot currently ship because of the same unpaid $840 invoice affecting Ticket 101.

I would also expect Boss to involve Accounting, potentially in parallel, because the club has requested a bulk discount and we need to understand the financial implications.

Accounting should use evaluate_price_override to examine whether a proposed discount would preserve an acceptable margin. The hoodies have a unit cost of $22 and a list price of $58. I would expect Accounting to evaluate at least one possible discounted price, such as $50, while making clear that this is a hypothetical option rather than a price requested by the customer.

Accounting should also consider the shop's cash position and other outstanding obligations before recommending additional inventory purchases. The $160 remaining after rent and the vendor invoice may constrain our ability to restock.

I recognize that the database's $22 unit cost does not necessarily equal the vendor's actual restocking price, so the agents should not assume the precise purchase cost without confirming it.

Once Inventory and Accounting have assessed the situation, Boss should involve Customer Service to draft a response explaining that the shop is reviewing the bulk order, inventory availability, and possible pricing.

I would not expect Facilities to be involved because this ticket does not concern the physical shop or lease.

I expect the ticket to require further decisions about the proposed discount, whether to fulfill the 8 available hoodies immediately or wait for the remaining 12, and whether restocking is financially feasible. The agents should not promise a discount, delivery date, or purchase commitment without the necessary information and approval.

Expectations across all three tickets

I also expect the agents to recognize that the tickets are financially interconnected.

Ticket 102 has a time-sensitive rent obligation. Ticket 101 involves an unpaid vendor invoice that is also preventing restocking for Ticket 103. The combination of the $2,400 rent payment and $840 invoice would leave only $160 in available cash.

My expected priority order is:

Ticket 102 first because rent has a specific upcoming deadline.

Ticket 101 second because clearing invoice 501 could unlock restocking for both customer orders.

Ticket 103 third because the discount and restocking decisions depend partly on the vendor situation and remaining cash.

This is my predicted order, not a requirement that the agents must follow. We will compare my expectations with their actual behavior later.

I would expect Accounting to consider all known outstanding obligations when assessing cash availability, rather than treating each ticket as though it has the entire $3,400 available. Please document this expectation in the dashboard, but do not change the backend or implement new payment-coordination logic as part of this problem.

Dashboard implementation requirements

Please build the HTML dashboard with:

One clickable tab for each of the three tickets, plus Cash and Reflection.

An Expected section on each ticket tab that clearly identifies the first agent Boss should call and why.

The anticipated sequence of additional agent delegations, including which agents may communicate directly with one another.

The specific MCP tools expected to be used and what each should help establish.

The anticipated decisions, dependencies, and approval requirements.

A clearly separated Actual section reserved for later comparison.

Empty Cash and Reflection tabs for future problems.

Please make the dashboard clean, readable, and easy to navigate. I want to be able to double-click output/desk_tickets.html and view it directly in a browser without needing to start the backend or React application.

Do not run the agents, resolve tickets, make payments, update ticket statuses, or modify the database. This problem is strictly about documenting my expectations before observing the actual agent workflows.

Please preserve the existing project structure and files. Once the dashboard is created, tell me what you implemented and confirm that all five tabs work and that the Actual sections remain empty.

Reason for prompt 2: I wanted CC to help me better undertsand what was going on before i wasted time extrapolating what i think agents are supposed to do/ handle information without precise context 



# Problem 7
Prompt 1: Now I want to work on Problem 7 which is about creating the backend that will eventually connect our agent system to the React dashboard.

We've already spent time building the five agents, the MCP tools, and the planning dashboard. I want to make sure we're building on that existing work rather than creating new systems that duplicate what we've already implemented.

The goal here is to use FastAPI in `backend/main.py` to create the routes that will allow a human to interact with the Campus Customs operation through the frontend.

There are a few things I need the backend to be able to do.

First, I want the dashboard to be able to pull up all three tickets and see their current statuses, including whether they're still open or have been resolved. I also want to be able to select an individual ticket and tell the existing agent team to begin working on it. Boss should remain responsible for coordinating the other agents, and their delegation process should follow the system we built in Problem 5.

Another important part of the dashboard is visibility into what the agents are actually doing. I want a route that retrieves recent agent activity, including which agent is working, what tools it has called, what information it found, and whether it delegated anything to another agent. We already started building an audit trail, so I'd prefer to use those actual records instead of generating a separate set of activity messages just for the frontend. Ideally, the dashboard should be able to refresh and show new activity as it happens.

The financial side is especially important to get right. I want the agents to be able to investigate invoices, check balances, and prepare recommendations for payments or purchases, but I do not want them to have the authority to move money themselves. The backend needs a route through which a human can review and explicitly approve a proposed transaction. Only after that approval should the appropriate MCP tool be allowed to record the payment and update the database.

Please make sure the system checks that the payment hasn't already been made and that the shop actually has enough cash to cover it. If the balance is insufficient, the transaction should be rejected rather than allowing the account to go negative. I also don't want the approval route to accept arbitrary payments that were never prepared for review.

Separately, I need the frontend to be able to request the current checking balance. That number should come from the actual `cash_accounts` data and should change only when an approved payment has been recorded, not when an agent merely recommends one.

I also want a way to reset the working database to its original state. Since we'll eventually be running the agents on all three tickets and comparing their actual behavior against my expectations, being able to start with clean data is important. The reset should restore `data/campus_customs_new.db` from `data/campus_customs.db` without modifying the original. Please make sure it can't interrupt an active transaction or agent run, and that our accumulated audit history isn't accidentally erased.

One architectural detail I want to preserve from Problem 5 is that the MCP server remains the only way the agents and backend access the shop's operational data. I don't want FastAPI to introduce another set of direct SQLite queries that bypass the tools we've already built. The backend should be responsible for receiving requests, coordinating the agents, managing approval actions, and returning information to the frontend. The MCP server should remain responsible for reading and updating the database. If the reset requires an additional MCP maintenance tool, that's fine.

Please use clear, consistent endpoint names and JSON responses so that connecting the React frontend in the next problem will be straightforward. I also want sensible handling of things like nonexistent tickets, duplicate approvals, insufficient cash, or a tool failing during an agent run.

Once the routes are in place, please start or verify the FastAPI server from the `backend/` directory using `uvicorn main:app --reload --port 8000`. I want to know that the backend can run at `http://localhost:8000` and that its routes are accessible. You can test the endpoints without completing a full ticket-resolution run or making unnecessary changes to the database.

Finally, please add a section to our existing `output/harness.md` listing each backend route, its URL and HTTP method, and a short explanation of what it does. Obviously keep everything prior there 
Before finishing, I'd like you to review the implementation for consistency with what we've already built, especially the MCP-only data access rule and the requirement that financial transactions cannot happen without human approval.
Can you give me a summary of what you did after? also  let's stay focused on the backend rather than moving ahead to the React dashboard

# Problem 8
Prompt 1: Ayyyy lets do problem 8 now. We need to build the frontend for Campus Customs. We've already created the MCP server, five-agent team, FastAPI routes, and ticket planning dashboard. I want to bring these pieces together into an actual interface where someone running the shop could supervise the agents and understand what they're doing.

Please build the frontend in `frontend/` using React, Vite, and TypeScript, connecting it to the FastAPI backend we created in Problem 7.

I want the dashboard to feel like an operations desk for a small business. The idea is that a human should be able to quickly understand what needs attention, which agents are working, what decisions they're making, and when human intervention is required. I want the vibe to be friendly and interactive with a sleek UI. 

**Dashboard layout and functionality**

I'd like the three open tickets to be one of the main focal points of the page. Each ticket should show its ID, a short description of the issue, and its current status. I should be able to select any ticket and start the agent team working on it directly from the dashboard.

Once a ticket is running, I want to see the agents' activity as it unfolds. Rather than just showing a stream of technical logs, please make it easy to distinguish the five agents and understand their individual contributions. Boss, Inventory, Accounting, Facilities, and Customer Service should each have a recognizable visual identity, so I can follow which specialist is speaking, investigating something, calling an MCP tool, or delegating work.

I think it would be interesting to present the activity as a collaborative workflow, where I can see how a ticket moves between agents and why one agent calls on another. I want the interface to communicate that this is a team working together, not five isolated chatbots.

When a ticket run finishes, the dashboard should provide a short summary of what each participating agent accomplished. The ticket status should also update to reflect the actual outcome. Please distinguish between a ticket that is fully resolved and one that is still waiting for approval or blocked by another issue. I don't want the interface to imply that a ticket is resolved simply because the agents have finished their analysis. We need a focus on communication and truth here! 

**Human approvals and cash visibility**

I want financial decisions to be especially visible. If an agent recommends paying an invoice, making a rent payment, or approving a purchase, that request should appear clearly in the dashboard for a human to review.

The approval interface should explain what the payment is for, how much it costs, and what the checking balance would be afterward. I should be able to approve the proposed transaction through the backend, but the frontend should never directly modify financial data.

The current checking balance should remain visible somewhere prominent on the page. I want it to refresh after an approved payment so that the effect of financial decisions is immediately apparent.

Because we identified that the three tickets share financial constraints, it would also be useful for the interface to distinguish between the actual cash balance and payments that have merely been proposed. Please use the information available from the backend rather than inventing financial values.

**Design direction**

Visually, I want the dashboard to feel polished, modern, and intentionally designed for a real small-business operator.

I'd prefer a clean editorial style over a typical developer dashboard. Use thoughtful typography, a restrained color palette, clear spacing, and a strong visual hierarchy. The interface should feel professional but still have some personality appropriate for a campus merchandise business.

I imagine the page organized around three priorities: what needs attention, what the agents are currently doing, and what decisions require a human. The most important information should be understandable at a glance.

Please make the five agents visually distinct without relying on excessive colors or clutter. I'd like the design to communicate their different responsibilities through consistent labels, icons, and subtle visual treatments.

I'd also like the interface to make completed work feel satisfying and easy to review. Resolved tickets should look meaningfully different from open ones, and the user should be able to see what happened without digging through the entire audit trail.

Feel free to make thoughtful design choices that improve the experience, but prioritize usability and clarity over decorative elements.

**Connecting the frontend and backend**

Please use the FastAPI endpoints we implemented in Problem 7 rather than creating mock responses or hardcoded ticket data.

The frontend should communicate with the backend at `http://localhost:8000`. Please configure the necessary API connection and make sure the backend permits requests from the Vite development origin, typically `http://localhost:5173`.

The dashboard should retrieve ticket information, start individual agent runs, refresh agent events, display results, handle human approvals, and retrieve the checking balance.

Please also provide a way to reset the working database for a clean run, using the existing backend reset functionality. Since resetting affects the entire shop state, it should require an explicit confirmation.

I want the interface to handle loading states, unsuccessful requests, and backend errors gracefully. It should also remain usable if an agent run takes some time to complete.

**Running and testing the dashboard**

Once the frontend is built, please verify that it can be started from the `frontend/` directory using:

`npm run dev`

Make sure the React application loads correctly in the browser and can communicate with the FastAPI backend.

Please test the connections where possible, but do not run the full three-ticket resolution process or approve actual payments just to demonstrate the interface. We will do that in the later problems.

**Documenting the design**

Please create `output/design.md` explaining the design choices we made.

I want this to go beyond simply listing the components. Explain why the dashboard is organized the way it is, how the visual design helps distinguish the five agents, how ticket statuses and completed work are communicated, and why the checking balance and human approval requests are given prominence.

Please also describe the more creative decisions that make the dashboard feel like an actual workspace for supervising a team rather than a generic administrative interface.

Keep the explanation in a natural, thoughtful voice that reflects the reasoning behind the design rather than sounding like a technical specification.

Before finishing, please review the implementation to make sure the frontend is actually connected to our existing backend and that all seven required dashboard capabilities work as intended.

Let me know what files you created or changed, which features you were able to test, and whether anything still needs attention. Please don't move ahead to the final ticket runs or GitHub submission yet.

Prompt 2: 
In terms of aesthetic can you add Yale emblems all over the page without being overwhelming (like the residential college crests, bulldogs, sketches of any human figures that have been critical in Yale's history) 

Reason for Prompt 2: 
I wanted to decorate the page more in our labubu-like vibes from class. 



# Problem 9
Prompt 1: Let's now do problem 9 where we actually put the Campus Customs multi-agent system to work on all three open tickets.

I now want to run the system, observe how the agents collaborate, and compare their actual behavior against what I anticipated in Problem 6.

I want to be especially careful about the financial side of this exercise, since our three tickets share some of the same cash and vendor constraints. I also want to make sure we satisfy all the deliverables for both panels of Problem 9.

### 1. Prepare for the full run

Before starting, please reset `data/campus_customs_new.db` to match the original `data/campus_customs.db`, so that none of our earlier tests influence the results. Keep the original database untouched.

After resetting, confirm the starting checking balance from the working database and record it for our final cash reconciliation.

Then help me run tickets 101, 102, and 103 through the React dashboard using our actual PydanticAI agents and MCP tools.

I want the agents to investigate the tickets, delegate work as needed, and use the information in the database to make decisions. Please do not substitute simulated agent responses or manually construct outcomes that bypass the system we've built.

Our objective is to get all three tickets to a truthfully resolved state through the agent system. If a ticket is initially blocked, identify the specific obstacle, determine whether the agents or a human can legitimately address it, and continue the workflow until it is resolved where possible.

Do not treat an initial blocked or awaiting-approval status as the end of the process. never mark a ticket resolved unless the necessary actions have actually occurred.

### 2. Run and resolve the three tickets

For Ticket 101, I expect the agents to investigate the missing size S tee, determine why Bulldog Print Co cannot restock, and address the unpaid vendor invoice. The agents should identify any required payment approval and prepare the appropriate next steps.

For Ticket 102, I want the team to handle the upcoming $2,400 rent payment, verify the lease and payment status, and prepare the payment for approval before the due date.

For Ticket 103, the agents need to evaluate the Yale AI Club's request for 20 medium hoodies at a bulk discount, including the inventory shortage, vendor restrictions, pricing margins, and any financial constraints affecting restocking.

Please make sure Accounting considers the financial obligations across all three tickets rather than evaluating each ticket as if it has access to the entire starting cash balance.

I want to observe how the agents handle these shared dependencies and whether their decisions remain financially consistent.

My predicted priority order was Ticket 102 first, then 101, then 103, because rent has an approaching deadline and clearing invoice 501 could help unlock restocking for both customer orders. However, I want the actual agent behavior to be documented faithfully, even if it differs from my expectations.

### 3. Human approvals and payment safeguards

This is especially important: the agents should never execute payments or purchases independently.

If a payment or purchase requires approval, please surface the request through the dashboard so I can review it. Do not automatically approve transactions or simulate a human approval.

Before I approve anything, I want to see the purpose of the payment, the amount, the current checking balance, and the projected balance afterward.

Once I explicitly approve a payment, the system should record it through the MCP server and update the relevant database tables.

If there isn't enough cash to cover a proposed transaction, the system should refuse it. No negative balances, duplicate payments, or payments that bypass the approval process.

Please stop and ask me for approval whenever a financial transaction requires human authorization. Do not interpret my request to complete Problem 9 as permission to approve payments on my behalf.

### 4. Document the actual agent behavior

Once we've run each ticket, please update the existing `output/desk_tickets.html` file from Problem 6.

On each ticket's tab, fill in the Actual section using the real agent activity from the run.

For each ticket, I want to see:

- Which agents participated and what each contributed.
- Which agent Boss delegated to first and why.
- Any additional delegations between agents, including direct specialist-to-specialist communication.
- The specific MCP tools used and what information they returned.
- The decisions made, actions completed, and final outcome.

Please preserve my original Expected sections exactly as they were written. The point is to compare what I predicted against what the system actually did, including any differences or unexpected behavior.

If an agent behaved differently from what I anticipated, document that rather than adjusting the original plan to make the results appear consistent.

### 5. Complete an itemized cash reconciliation

On the Cash tab of `output/desk_tickets.html`, please document the financial impact of the full run.

Start with the checking balance immediately after the database reset.

Then, for each ticket, identify any actual payment or purchase that changed cash, explain what it was for, and record the dollar amount.

I want the Cash tab to include an itemized table showing:

- The starting checking balance.
- Each completed payment or purchase, identified by ticket and purpose.
- The dollar amount deducted for each transaction.
- The running checking balance after each transaction.
- The final checking balance after all three tickets have been processed.

Based on our earlier database review, the expected starting balance is $3,400. We also identified a $2,400 rent obligation and an $840 unpaid vendor invoice. If both are approved and paid, they would leave $160.

However, these figures are only our expectations before the run. Please use the actual recorded transactions, amounts, and payment sequence when preparing the final reconciliation.

Distinguish clearly between payments that were merely proposed and payments that were actually approved and executed. Only completed transactions should reduce the checking balance.

Finally, verify that the ending balance matches the value recorded in `cash_accounts` in `data/campus_customs_new.db`.

This reconciliation is particularly important because the assignment explicitly states that incorrect cash calculations will lose points even if all three tickets are marked resolved.

### 6. Save the resolved ticket results

Please create `output/resolved_tickets.json` with a record for each of the three tickets.

Each record should include the ticket ID, final status, a short explanation of the outcome, what each participating agent contributed, and any human approvals involved.

The information should reflect the actual agent runs and database state rather than our earlier predictions.

### 7. Capture the final React dashboard

I also need `output/resolved_board.html`, which should be a standalone HTML page that I can double-click to open in a browser.

Please capture a separate screenshot of the actual React dashboard showing the final state of Ticket 101, Ticket 102, and Ticket 103.

Embed all three screenshots into `output/resolved_board.html`, with clear labels identifying each ticket. Make sure the page opens independently in a browser and that all three images display correctly.

These must be genuine screenshots of the running React dashboard, not a newly generated HTML approximation of what the dashboard would look like.

If capturing actual screenshots requires a browser tool or another capability that isn't available, please tell me rather than substituting fabricated screenshots.

### 8. Preserve the audit trail

Continue appending the real agent activity to `output/audit_trail.json`.

I want the audit trail to reflect what actually happened during the runs, including agent actions, delegations, MCP tool calls, outcomes, and relevant approval events.

Do not overwrite the existing audit history or fabricate records to fill gaps.

Please also ensure that no API keys or sensitive credentials appear in the audit trail.

### 9. Finish the harness documentation

Please finish updating `output/harness.md` so that it accurately documents the complete system we've built.

It should cover:

- The database tables and their relevance to the agents.
- All MCP tools and the tables they access.
- The five agents, their responsibilities, and how they delegate work.
- The FastAPI routes and what each endpoint does.
- The React dashboard and its major features.
- The safety rules governing payments, customer communications, database access, and agent delegation.

Please preserve the documentation from earlier problems and make sure the descriptions reflect the actual implementation.

### 10. Final verification against the assignment

Before telling me Problem 9 is complete, please perform a final review against the requirements of both Panel A and Panel B.

Specifically, confirm that:

1. The working database was reset before the full run, the original database remained untouched, and the starting checking balance was recorded.
2. Tickets 101, 102, and 103 were processed through the real agent system, with genuine resolution pursued for each.
3. The Actual sections in `output/desk_tickets.html` document the agents involved, their delegations, and MCP tools used, while the original Expected sections remain unchanged.
4. The Cash tab includes an itemized reconciliation of the starting balance, each ticket's actual cash impact, and the final balance, which matches `cash_accounts`.
5. `output/resolved_tickets.json` includes the ID, final status, outcome, agent contributions, and human approvals for all three tickets.
6. `output/resolved_board.html` contains three actual screenshots of the React dashboard, one for each ticket, and opens independently in a browser.
7. `output/audit_trail.json` contains appended records from the real agent runs.
8. `output/harness.md` covers all required components of the system, including the database, MCP tools, five agents, API routes, dashboard, and safety rules.
9. All financial transactions followed the human approval process, no negative cash balances occurred, and no payment was recorded more than once.
10. All final ticket statuses are supported by the actual actions completed and the working database.

If anything is incomplete, please identify it specifically rather than reporting that the assignment is finished.

I also want you to distinguish between what was successfully tested and verified, what still requires my approval, and what remains unresolved.

Please do not artificially mark tickets resolved, change database values to manufacture a successful outcome, or create evidence of agent activity that did not occur.

Let's work through this carefully, stopping whenever my approval or input is necessary, and complete Problem 9 before moving on to the final GitHub submission.

Prompt 2: 
Thank you. I think the results are useful, particularly because the agents recognized how financially interconnected the three tickets are and that the same unpaid vendor invoice affects both customer orders.

I'd like to proceed with the following decisions, but I also want to make sure we're interpreting what it means to "resolve" a ticket correctly within the scope of this assignment.

**First, my approval decisions:**

I approve the $2,400 rent payment for Ticket 102 and the $840 payment of invoice 501 for Ticket 101. Please process both through our existing human-approval workflow, using my explicit authorization here, and verify that each payment is recorded exactly once. If those are the only cash transactions, our checking balance should decrease from $3,400 to $160.

I also approve the proposed restock of one size-S Classic Bulldog Tee for Ticket 101. Since our system doesn't currently have a purchase-order table or a mechanism for simulating inventory arrivals, please record this as an approved restock decision rather than pretending the item has physically arrived or that a purchase order was placed.

For Ticket 103, I approve the proposed 10% bulk discount, bringing the price to $52.20 per hoodie. I think this preserves a reasonable margin while still recognizing the club's larger order.

Regarding fulfillment, I would propose offering the eight medium hoodies we currently have and giving the customer the option to wait for the remaining 12. I don't want the system to assume the customer has accepted a partial order or commit to a restock we cannot currently fund.

Please also distinguish between the $22 accounting unit cost and the actual vendor purchase price. Unless the database confirms the latter, we should not treat the estimated $264 restock cost as a verified financial obligation.

**Second, I want to clarify how we should define ticket resolution in this assignment.**

Problem 9 explicitly asks us to run all three tickets until each is resolved. I want to satisfy that requirement, but I also don't want to misrepresent what the agents have actually accomplished.

Before determining the final statuses, please inspect the existing ticket schema, the status-handling logic in our backend, and the assignment's broader business rules to determine what constitutes a legitimate resolution in this simulated environment.

My question is whether "resolved" means that the agents have completed all actionable work available to them, including securing the necessary approvals and drafting customer communications, or whether it requires the underlying real-world obligation to be fully completed.

For example:

- Ticket 102 seems straightforward: once rent is approved, paid, and recorded, I would consider the issue resolved.
- Ticket 101 is more nuanced. Once invoice 501 is paid, the restock is approved, and the customer response is drafted, the agents may have completed everything the simulation allows them to do. However, the tee still has not physically arrived.
- Ticket 103 is similarly complicated. We can approve the discount and propose a partial fulfillment arrangement, but the remaining inventory shortage and the customer's acceptance are still outstanding.

Please determine whether the system can legitimately treat these as resolved operational tickets once the agents have completed their available responsibilities, while still clearly documenting any outstanding physical fulfillment or customer dependencies.

If that interpretation is supported by the assignment and our implementation, I would prefer to use it so that we can meet the requirement to resolve all three tickets. But please don't change the definition of resolution simply to make the results look successful.

If the current ticket schema or backend logic cannot adequately represent these distinctions, explain what is missing and recommend the smallest reasonable adjustment. I don't want us inventing inventory arrivals, customer acceptances, purchase orders, or payments that never happened.

**Third, rerun the agents and verify the results.**

Once the approved decisions have been recorded, please rerun the agents on all three tickets so they can evaluate the updated state and determine what work has been completed.

I want the agents themselves to determine the appropriate final outcomes through the existing workflow rather than manually changing ticket statuses.

Please make sure the reruns continue to use the actual PydanticAI agents and MCP tools, with all activity appended to our audit trail.

Afterward, show me:

- The final status of each ticket and the reasoning supporting that status.
- Which payments were actually recorded and whether they were recorded only once.
- The final checking balance, reconciled against `cash_accounts`.
- Any remaining customer, inventory, or fulfillment dependencies.
- Whether the system's definition of resolution is consistent with the assignment requirements.

Please stop and explain any ambiguity or implementation issue that could materially affect the accuracy of the results.

**Finally, let's hold off on completing the Problem 9 deliverables until we've verified the ticket outcomes.**

Once we're confident that the statuses are legitimate, we can update the Actual sections of `output/desk_tickets.html`, complete the Cash tab, and prepare `resolved_tickets.json`, `resolved_board.html`, and the final harness documentation.

Please preserve the original Expected sections exactly as written so that we can compare my predictions with the actual agent behavior, including any unexpected delegations or decisions.

My priority is to meet the assignment's requirement that all three tickets be resolved while maintaining an accurate record of what the agents actually did and what remains outstanding. Now that we've completed the clean rerun of all three tickets, I'd like to verify that the system is functioning correctly and that our results are accurate before preparing the final Problem 9 deliverables.
I want to be thorough here, particularly because we had to reset and rerun after the issue with the approver names. Please work through the verification first, report your findings, and only then move on to the deliverables once we've established that everything is consistent.
Part 1: Verify the clean rerun
1. Confirm the database and ticket statuses
Please inspect data/campus_customs_new.db and confirm that:
* The working database was reset to the original state before the final run.
* The original data/campus_customs.db remains untouched.
* Tickets 101, 102, and 103 were all processed through the actual PydanticAI agents and MCP tools.
* Each ticket's final status is supported by the actions that actually occurred.
* No ticket was prematurely or artificially marked resolved.
Please pay particular attention to our earlier discussion about what constitutes a legitimate resolution in this simulation. I want to satisfy the assignment's expectation that all three tickets be resolved, but without pretending that inventory arrived, customers accepted offers, or transactions occurred when they did not.
If any ticket remains open, please explain exactly why and whether there is a legitimate way to complete the remaining work within the existing system.
2. Verify all four approval decisions
Please check that the following decisions were accurately recorded during the clean rerun:
* Ticket 102: $2,400 rent payment to Elm City Properties.
* Ticket 101: $840 payment of invoice 501 to Bulldog Print Co.
* Ticket 101: Approval of the one size-S tee restock.
* Ticket 103: Approval of the 10% bulk discount, bringing the hoodie price to $52.20 per unit.
Confirm that the approver names are now recorded correctly, that the underlying name-encoding issue has been fixed, and that the approvals correspond to the authorizations I provided.
Also verify that no approval was duplicated or carried over incorrectly from the earlier run.
3. Reconcile the cash
Please independently check the financial records in the working database.
Our expected cash reconciliation, assuming only the two approved payments were executed, is:
* Starting checking balance: $3,400
* Rent payment: −$2,400
* Vendor invoice 501: −$840
* Expected ending balance: $160
Confirm that the actual payments table supports these transactions, that each payment was recorded exactly once, and that the ending balance in cash_accounts matches the calculation.
Also confirm that approving the tee restock and hoodie discount did not incorrectly reduce cash, since those decisions alone do not constitute recorded payments.
If the actual transactions differ from this expectation, please explain the difference rather than adjusting the records to fit.
4. Verify the agent activity and audit trail
Please inspect the actual run logs and output/audit_trail.json to confirm that:
* The Boss and specialist agents genuinely participated in the ticket workflows.
* Agent-to-agent delegations occurred through the system rather than being simulated.
* MCP tool calls were made against the working database.
* The audit trail preserves the original error and reset history while clearly distinguishing the final clean run.
* The final run's recorded events are sufficiently detailed to reconstruct which agents worked on each ticket, what they delegated, and which tools they used.
Please distinguish actual observed behavior from the Expected plans we wrote in Problem 6.
5. Report the verification results before proceeding
Before preparing the deliverables, please give me a concise verification report with the final status of each ticket, all recorded approvals, the starting and ending checking balances, any remaining dependencies, and whether the clean rerun passed the checks above.
If anything is inconsistent or incomplete, flag it rather than quietly correcting or overlooking it. Please wait for my confirmation before moving on to Part 2.
Part 2: Complete the Problem 9 deliverables after verification
Once I've reviewed the verification report and confirmed we can proceed, please prepare all of the following deliverables, as required by Panels A and B.
1. Complete output/desk_tickets.html
Open the existing file from Problem 6 and update the Actual section for each ticket: 101, 102, and 103.
For each ticket, document:
* Which agents participated.
* Which agents the Boss delegated to first.
* Any further delegations between specialist agents.
* The specific MCP tools used.
* The actions and decisions made.
* The final outcome and status.
Preserve the original Expected sections exactly as written. I want the difference between my initial predictions and the agents' actual behavior to remain visible.
Please do not replace the Actual sections with generic descriptions of how the system is supposed to work. They need to reflect the real clean rerun.
2. Complete the Cash tab in output/desk_tickets.html
Create an itemized financial reconciliation showing the starting checking balance after the reset, every actual payment or purchase associated with each ticket, the amount deducted, and the running balance after each transaction.
Clearly identify tickets that did not generate a cash outflow.
The final checking balance must match cash_accounts in the working database.
Please make the presentation easy to follow so someone grading the assignment can independently verify the arithmetic.
3. Create output/resolved_tickets.json
For each ticket, include its ID, actual final status, a concise outcome summary, what each agent contributed, and any human approvals involved.
Make sure the JSON reflects the final verified database state and agent activity.
4. Create output/resolved_board.html with real screenshots
This deliverable is especially important.
The assignment requires a standalone HTML page containing an actual screenshot of the React dashboard for each of the three tickets.
Please use Playwright or another available browser automation tool to open our running React dashboard at http://localhost:5173.
Capture three separate screenshots showing the final dashboard state of Tickets 101, 102, and 103.
Embed those screenshots into output/resolved_board.html with clear labels for each ticket.
Please ensure that:
* These are genuine screenshots of the running React application, not recreated or simulated images.
* Each screenshot clearly shows the relevant ticket's final state.
* The HTML page can be opened independently by double-clicking it.
* All three screenshots render correctly without requiring the backend to be running.
If browser automation is unavailable, please explain what is missing rather than substituting fabricated screenshots.
5. Preserve and finalize output/audit_trail.json
Make sure the audit trail includes the real activity from the final clean run, including agent interactions, delegations, MCP tool calls, decisions, and approval events.
Preserve the earlier error and reset history as appropriate, but make the final graded run clearly identifiable.
Do not fabricate missing events or overwrite the historical audit records.
6. Finish output/harness.md
Please ensure the harness comprehensively documents the entire system we've built, including:
* Every database table and its purpose.
* Every MCP tool, the tables it accesses, and what it enables the agents to do.
* All five agents and their responsibilities.
* The delegation structure and full connectivity between agents.
* Every FastAPI route and its function.
* The React dashboard and its features.
* The safety rules around human approvals, payments, customer communications, database integrity, and token usage.
Please preserve useful documentation from the earlier problems and make sure the final version accurately reflects the actual implementation.
Part 3: Final quality check
After completing the deliverables, please perform one last review against the requirements of both Problem 9 panels.
Check that every required file exists, opens or parses correctly, and contains the expected information.
In particular, verify that:
1. All three ticket outcomes are accurately documented and supported by the real run.
2. The Expected sections remain unchanged and the Actual sections reflect observed agent behavior.
3. The Cash tab reconciles exactly with the database.
4. resolved_tickets.json contains all required information for all three tickets.
5. resolved_board.html contains three genuine screenshots that display correctly.
6. The audit trail preserves the real agent activity and the clean rerun.
7. harness.md covers the database, MCP tools, five agents, API routes, dashboard, and safety requirements.
8. No fabricated transactions, approvals, customer responses, or agent events were introduced.
9. No API keys or sensitive credentials appear in the deliverables.
Please also confirm that the files are organized consistently with the expected GitHub submission structure from Problem 11.
My goal is to have Problem 9 fully complete, accurate, and ready for grading before moving on to the next problem.
For now, begin with Part 1 only. Give me the verification report and wait for my approval before generating the final deliverables.


Reason for Prompt 2: 
I asked CC to wait on a lot of decision gates to have me manually verify so this interaction was a consequence of that. We had a lot of back and forth as I kept asking it to verify its work in line with graidng standards. I then asked it for the deliverables for Probelm 9 seprately after all of these verifications which is why it took so long and this problem in particular was so laborious for CC. 



# Problem 10
Prompt 1: Awesome you're doing a really great job. Thank you for all of the work on problem 9. Let's go on to Problem 10. This problem requires me to evaluate how the agents actually performed, compare their behavior against my original expectations, and consider the advantages and limitations of the multi-agent architecture we built.

Before writing the reflection, I want to understand the evidence from our project so I can develop my own conclusions and write the answers in my own voice.

Please do not write the final reflection or modify the Reflection tab yet. Instead, review our completed application and prepare a detailed, evidence-based report organized around the five questions below.

The assignment emphasizes that every answer must be tied directly to our Campus Customs application, the three tickets we ran, and the actual results. Generic commentary about AI agents will not be sufficient.

First: Review the project evidence

Please examine the following materials before preparing your report:

output/desk_tickets.html, particularly the original Expected sections, the completed Actual sections, and the Cash tab.

output/audit_trail.json, including the final clean agent runs, delegations, MCP tool calls, and approval events.

output/resolved_tickets.json, including final statuses and outcomes.

The five agent prompts and implementation under backend/.

The MCP tools implemented in mcp_server/.

The FastAPI backend and React dashboard, where relevant to understanding what the agents could and could not accomplish.

Any available records of the earlier errors, corrective changes, and reruns.

Please use the final clean runs as the primary evidence for evaluating agent performance, while discussing earlier errors and corrections separately when they reveal meaningful limitations.

Do not assume that something occurred simply because it was planned or mentioned in an earlier conversation. Verify important claims against the actual project files.

Question 1: How would I evaluate the agents' performance on each ticket, and why?

Please evaluate Tickets 101, 102, and 103 separately.

For each ticket, explain:

Which agents participated and what each contributed.

Whether the Boss delegated work effectively.

Whether the agents correctly identified the relevant business problem.

Whether they used the appropriate MCP tools and database information.

Whether their conclusions and proposed actions were financially and operationally sound.

Where the agents demonstrated useful coordination or specialization.

Where they were inefficient, repetitive, confused, or unable to complete a task.

Whether they ultimately accomplished the work available within the simulation.

Please be candid and analytical rather than automatically evaluating the agents positively because the final system worked.

I am particularly interested in whether the agents demonstrated sound business judgment, not merely whether they successfully called tools.

Use concrete evidence such as the unpaid $840 vendor invoice, the $2,400 rent obligation, the inventory shortages, the hoodie discount calculation, and the cash constraints.

Question 2: For each ticket, how did Actual compare with my original Expected plan?

Please read my original Expected sections in output/desk_tickets.html and compare them directly against the Actual sections and audit trail.

For each of the three tickets, explain:

Which parts of my predicted workflow were accurate.

Which agents I expected the Boss to contact first.

Which agents the Boss actually contacted first.

Which specialist-to-specialist delegations occurred.

Whether the agents involved specialists I had not anticipated.

Whether any additional handoffs improved the quality of the outcome or introduced unnecessary complexity.

Whether the agents used the MCP tools I anticipated.

What surprised us about the actual process.

Please identify the specific delegation sequences and tool calls where the logs support them.

I want to preserve the distinction between my predictions and what actually happened, rather than rewriting the Expected plan retrospectively.

Also consider whether the agents' ability to delegate freely created more collaboration than the business problem actually required.

Question 3: What would have been simpler with one agent using tools, and why?

I want to critically evaluate whether our five-agent architecture was necessary for the three tickets we handled.

Please identify which tasks could reasonably have been completed by a single agent with access to the same MCP tools.

Consider:

Whether the Boss sometimes delegated to too many specialists simultaneously.

Whether agents repeated database lookups or requested information already available.

Whether specialist-to-specialist handoffs added useful expertise or unnecessary overhead.

Whether multiple agents complicated approval handling or stopping conditions.

Whether a single agent could have managed straightforward tasks such as checking rent, verifying a payment, or calculating a proposed discount.

Whether the interconnected inventory, vendor, and accounting constraints justified using multiple agents in more complicated situations.

Please distinguish between the benefits of specialization and the costs of coordination.

I would also like you to consider whether the system's full connectivity was an advantage in practice or whether more selective delegation could have been more efficient.

Ground this discussion in specific examples from our three tickets, including the number of handoffs, repeated tool calls, and any coordination loops where those details are verifiable.

Question 4: Describe three new Campus Customs problems that our current agents and MCP tools could solve.

Please propose three realistic new business problems that Campus Customs might encounter and that our existing system could address without building additional tools.

For each proposed problem, explain:

The business situation and what needs to be decided or accomplished.

Which existing agents would participate.

Which specific MCP tools they would use.

What information those tools would retrieve or evaluate.

How the agents would coordinate to reach an outcome.

Why the current system has sufficient capabilities to address the problem.

Please make these problems meaningfully different from Tickets 101, 102, and 103, rather than simply changing the product or customer name.

I want the examples to demonstrate the range of our current system's capabilities while remaining realistic about its limitations.

If a proposed problem requires functionality that our MCP server doesn't currently support, do not classify it as something the system can already solve.

Question 5: Describe three new Campus Customs problems our current system could NOT solve, and what would be required to solve them.

Please identify three realistic business problems that the current five agents and MCP tools cannot fully handle.

For each problem, explain:

What the business would need to accomplish.

Why our current system cannot complete that task.

Which specific data, tools, or capabilities are missing.

What additional MCP tools would need to be developed.

Which existing agent could take responsibility, or whether a new specialist agent would be justified.

How the new capabilities would integrate with the existing system.

Please make these examples specific to Campus Customs and the architecture we actually built.

I am particularly interested in limitations that became apparent during our three ticket runs, such as the inability to execute purchase orders, confirm physical deliveries, receive customer responses, or model incoming revenue.

However, please also consider other realistic business challenges that would require extending the system.

I want the distinction between what our system can currently do and what it would need additional infrastructure to accomplish to be very clear.

Additional analysis: What were the most meaningful lessons from building and testing this system?

Separately from the five required questions, please identify three to five broader insights that emerged from our actual implementation.

Some themes I am interested in exploring include:

Operational resolution versus real-world fulfillment: We encountered a distinction between completing the work available to the agents and actually fulfilling the underlying customer order. What does this reveal about defining success in agentic systems?

Shared financial constraints: Our agents had to recognize that paying rent and clearing the vendor invoice would leave only $160 in checking. How did this complicate decisions across otherwise separate tickets?

Full connectivity versus efficient coordination: Did allowing every agent to contact every other agent improve outcomes, or did it sometimes create unnecessary handoffs?

Approval boundaries and stopping conditions: What did the duplicate approval loop for Ticket 101 reveal about the importance of clear agent instructions and recognizing completed decisions?

Reliability and auditability: What did the garbled approver-name issue, database reset, and subsequent reruns reveal about the challenges of making an agentic system trustworthy?

Please distinguish direct observations from your interpretations of what those observations suggest.

Panel B: Ground every answer in our actual Campus Customs application

The second panel of Problem 10 explicitly states that every reflection answer must be supported by evidence from our application and the three tickets we ran.

Please treat this as a central requirement throughout the report.

For each of the five questions, identify specific evidence from:

The Expected and Actual sections for Tickets 101, 102, and 103.

The Cash tab and the final checking balance.

The audit trail and actual agent delegation sequences.

The MCP tools and their observed uses.

The human approval workflow.

The final ticket outcomes and any outstanding dependencies.

Use specific ticket IDs, dollar amounts, agent names, MCP tool names, and observed behaviors wherever relevant.

For example, rather than saying that agents sometimes duplicated work, identify an actual instance of repeated delegation or tool use. Rather than saying that agents respected financial constraints, explain how they accounted for the rent payment, vendor invoice, and remaining checking balance.

Do not invent details, and do not rely on generic claims about the benefits or risks of AI.

Final output: Give me the evidence I need to write the reflection

Please organize your report under the five required reflection questions, followed by the additional lessons learned.

At the end, provide a comparison table for Tickets 101, 102, and 103 showing:

Expected delegation sequence.

Actual delegation sequence.

MCP tools used.

Most important differences between Expected and Actual.

Final ticket status.

Most significant success or limitation.

Where possible, cite the specific file, audit event, or section supporting important claims so I can verify them.

Please also identify any gaps in the evidence that would make a particular conclusion difficult to support.

Do not write the final reflection in my voice, do not populate the Reflection tab, and do not modify the project files at this stage.

I want to review the report first, develop my own assessment of the agents' performance, and decide which arguments are most compelling.

Once we've done that, I'll prepare my reflection in my own words and then have you insert the finished answers into the Reflection tab of output/desk_tickets.html.

For now, please focus on giving me a thorough, accurate, and specific factual foundation for all five questions in Problem 10.

Prompt 2: 
Ok here is my reflection. please include it in the reflection tab of the output/desk_tickets.html:
### 1. How would you evaluate the performance of the agents on each ticket and why?

Overall I think the agents did a pretty good job identifying the issues in each ticket and working within the constraints we gave them, but I was surprised by how much back and forth was needed to arrive at what were sometimes pretty straightforward decisions.

For Ticket 101, I thought the agents did a good job recognizing that the inventory issue was actually tied to a financial one. Inventory identified that we had no size-S tees available, but the bigger issue was that Bulldog Print Co couldn't ship anything until its overdue $840 invoice was paid. Accounting then considered that payment alongside the $2,400 rent obligation and correctly calculated that we would have only $160 remaining. I thought this was one of the better examples of the agents considering the broader business rather than just the ticket in front of them. That being said, the team struggled to recognize when an approval had already been given and kept requesting permission to move forward with the purchase order, so it ultimately took four runs and an adjustment to the prompts to get the ticket resolved.

Ticket 102 was probably the simplest issue, and ironically one of the clearest examples of the system being unnecessarily complicated. Facilities correctly identified the $2,400 rent payment, and Accounting verified that we had enough cash. However, Accounting initially evaluated the rent in isolation without considering the overdue vendor invoice. There were also multiple repeated tool calls, and the ticket required additional runs after a connection error and an issue with how rent payments were recorded. So while the agents ultimately reached the right outcome, I don't think the process was especially efficient.

For Ticket 103, I thought the agents demonstrated good financial judgment. They identified that we only had 8 of the 20 requested hoodies, calculated the profitability of a proposed 10% discount, and recognized that we couldn't afford to restock the remaining 12 after accounting for our other obligations. I appreciated that they didn't promise the customer something we couldn't deliver. My main criticism was that the first discount approval covered all 20 hoodies despite our limited inventory, so the scope had to be corrected and approved again.

Across the three tickets, I would say the agents were generally better at identifying and analyzing problems than they were at coordinating the steps needed to close them. The financial reasoning was largely sound, but getting the agents to act consistently on that information required more intervention than I anticipated.

### 2. For each ticket, how did Actual compare to the Expected plan you wrote earlier?

The biggest difference between my Expected plans and what actually happened was how quickly the Boss involved multiple agents. I had imagined a more sequential process where the Boss would first identify the primary specialist, let that agent investigate, and then bring in other agents as needed. Instead, the Boss generally contacted three specialists at once which I think contributed to some of the unnecessary overlap.

For Ticket 101, I expected Inventory to take the lead, with Accounting working in parallel and Customer Service brought in toward the end to draft a response. In reality, the Boss contacted all three immediately. I did correctly anticipate that Inventory would need to consult Accounting about the unpaid vendor invoice, but I hadn't expected Customer Service to independently contact Inventory or for Accounting to reach back out to Inventory. The additional communication didn't necessarily improve the outcome, especially since several agents ended up retrieving the same information.

For Ticket 102, I expected Facilities to lead and consult Accounting about the rent payment. That did happen, but the Boss also involved Accounting and Customer Service from the beginning. I had also expected Accounting to consider the rent alongside our other financial obligations, which it didn't initially do. It wasn't until the other tickets ran that the combined cash constraint was properly recognized, which made me realize how much the agents' decisions depended on the context they were given, even when the relevant information was technically available through their tools.

For Ticket 103, I expected Inventory and Accounting to work together on the stock shortage and discount request, followed by Customer Service drafting a response. Again, all three were contacted immediately, and there were more specialist-to-specialist handoffs than I anticipated. Accounting also evaluated a 10% discount at $52.20 rather than the $50 example I had originally considered. The agents correctly identified the inventory and cash limitations, but the discount needed to be approved a second time after its scope was narrowed to the eight available hoodies.

I think my original plans were generally accurate about which expertise each ticket required, but less accurate about how the agents would actually organize themselves. I had assumed that giving the Boss access to all five agents would allow it to delegate selectively, but in practice it seemed more inclined to involve everyone who might be relevant, even when that created redundant work.

### 3. What would have been simpler as one agent with tools, and why?

I actually think a surprising amount of this assignment could have been handled by one agent with access to the same MCP tools.

Ticket 102 is the clearest example. The task was really just to check the lease, verify whether rent had already been paid, confirm the cash balance, and prepare a payment for approval. A single agent could have completed those checks without passing information between Facilities, Accounting, and Customer Service. Instead, the first run involved six handoffs and twenty MCP calls, half of which repeated earlier calls.

There was similar duplication in the other tickets. For Ticket 101, both Inventory and Accounting repeatedly checked the same vendor invoice. For Ticket 103, three different agents checked the hoodie inventory. While each specialist had a different responsibility, they were often working with the same underlying information and I don't think having multiple agents necessarily made the process more informed.

I do think the multi-agent structure was more justified when a ticket required balancing different business considerations. For example, Ticket 101 wasn't just an inventory shortage. It involved vendor eligibility, overdue payments, available cash, and customer communication. Having specialized agents made sense conceptually, and I appreciated that Accounting was careful not to treat an estimated unit cost as a confirmed vendor quote.

Still, I came away thinking that specialization is only valuable when it produces a better decision or reduces the work required to reach one. In our case, the agents sometimes created more work for one another. I would probably redesign the system so that the Boss delegates more selectively and Customer Service receives the relevant findings once the operational decisions have been made, rather than conducting its own investigations.

I think the biggest learning for me was that giving agents the ability to communicate freely doesn't necessarily mean that the resulting collaboration is efficient, and in some cases more communication just introduced more opportunities for confusion.

### 4. Describe three new problems Campus Customs might face that this agent team could solve with the tools you built.

**First, the shop could evaluate a back-to-school promotion on an existing product.** For example, if Campus Customs wanted to discount its Yale Cap, Inventory could verify the 40 units in stock and Accounting could use the existing pricing tool to calculate the margin at different promotional prices. The caps currently cost $6 and sell for $22, so there is room to evaluate a discount without immediately selling below cost. Customer Service could then draft an announcement, and the Boss could prepare the pricing decision for human approval. The system couldn't automatically change the stored price, but it could complete the analysis and approval preparation.

**Second, the agents could assess whether Campus Customs can afford its next rent payment.** After resolving our original tickets, checking was down to $160, while another $2,400 rent payment would be due in October. Facilities could identify the upcoming obligation, Accounting could check the remaining balance, and the payment-preview tool would correctly refuse the payment because there isn't enough cash. The Boss could then flag the issue, and Customer Service or Facilities could draft a message to the landlord. I think this is a useful example because solving a problem doesn't always mean executing a transaction, sometimes the most valuable outcome is recognizing that the business cannot responsibly proceed.

**Third, the system could investigate a vendor payment dispute.** If Bulldog Print Co claimed that invoice 501 was still outstanding, Accounting could retrieve the payment history and verify that the $840 payment had already been recorded. Inventory could confirm that the vendor was no longer blocked from shipping, and Customer Service could draft a response with the payment details. This is a relatively simple task, but one where having access to a shared, auditable database would be valuable.

All three of these examples would require the issues to already exist as tickets since we didn't build a tool for creating new ones, but I think they show that the current system is strongest at investigating, evaluating, and documenting decisions using information already in the database.

### 5. Describe three new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain what additional tools and agents would be needed.

**The first limitation is actually placing purchase orders and tracking deliveries.** This became apparent with Ticket 101. Our agents could identify the inventory shortage, determine which vendor could potentially restock the product, and prepare a purchase order for approval. However, they couldn't actually send an order, confirm the vendor's price, or record the arrival of new inventory. To address this, I would add tools for creating purchase orders, recording vendor confirmations, and receiving shipments into inventory. Inventory could manage the process, while Accounting would handle the related payments and invoices. I don't think we would necessarily need another agent here, just a more complete set of tools.

**The second problem would be managing an actual customer order from beginning to end.** Ticket 103 illustrated this limitation. The agents could propose a discounted price and draft an offer for the eight hoodies we had available, but they couldn't send the offer, receive the club's response, reserve the inventory, or record a sale. We would need tools for approved outbound communication, customer replies, order creation, inventory reservations, and revenue recording. Customer Service could take responsibility for much of that workflow, with Accounting handling the financial side. For a larger operation, a dedicated order-management agent might make sense.

**The third limitation is forecasting the shop's cash needs over time.** Our agents were able to recognize that paying the rent and overdue invoice would leave just $160 in checking, but they couldn't really tell us what that meant for the business beyond the immediate tickets. We had no incoming revenue modeled, no way to advance the shop date, and no mechanism for forecasting future cash flows. I would expand Accounting's capabilities with tools for cash forecasting, recurring payment schedules, and projected sales. This would allow the agents to move beyond answering whether the shop can afford a payment today and toward understanding whether a decision is financially sustainable over the coming weeks.

What I found interesting about these limitations is that they weren't necessarily failures of the agents' reasoning. In many cases, the agents understood what needed to happen but simply didn't have the tools or authority to carry it out, which I think is an important distinction when evaluating what an agentic system can realistically accomplish. Also, while all three tickets were marked resolved in our system, that meant the internal decisions and approvals were complete, not that the physical products had been delivered or the customers had accepted our offers. I think that's a meaningful distinction because a system can successfully complete its own workflow without necessarily completing the underlying business transaction.

Reason for Prompt 2: I had to give CC the language to put on the interface after it helped me understand the idiosyncracies of our product. 