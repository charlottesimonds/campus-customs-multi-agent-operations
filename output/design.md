# Campus Customs Operations Desk: Design Notes

## The idea

Campus Customs is a small shop with a lot going on at once: a customer waiting on a tee, a landlord expecting rent in two days, and a student club asking for a bulk discount. All of it draws on one checking account. The person running it doesn't need a log viewer. They need a desk: somewhere to sit down, see what needs them, watch their team handle the rest, and step in when money is about to move.

So I designed the dashboard around three questions, in the order an operator asks them:

1. **What needs my attention?**
2. **What is my team doing about it?**
3. **What do I have to decide?**

Every part of the page answers one of those three questions. Anything that didn't serve one of them was left out.

## How the page is organized

**The top of the page is a sentence, not a chart.** "Today at the desk" opens with a plain headline written from live data, like "3 decisions waiting on you," or "The team is working" while a run is going. Below it, a quieter line counts runs in progress, resolved tickets, and pending approvals. A headline is the fastest thing to read, and it answers the first question before you've scrolled at all.

**The tickets come next, as cards.** The three tickets are the reason the page exists, so they sit right under the headline, side by side, at a size that invites you to read them. Each card has the ticket number in a large serif face, the subject, who sent it, their own words in italics, and the specific SKU, size, quantity, lease, or invoice it references. These are the details a shop owner would want to see before deciding whether to involve anyone. The status and the button to start the team sit at the bottom of the card, after the context, because you should understand the problem before you hand it off.

**Below the tickets, the page splits.** On the left is *Team at work*: the selected ticket and everything the agents did with it. On the right, pinned so it stays in view while you scroll, is the decision column: the checking balance and the approval queue. That split mirrors the job itself. Watching the team is ongoing and can take a while, while decisions are rare and important. Keeping the decisions fixed on the right means a payment request is never more than a glance away, even halfway down a long agent run.

## Five agents, one team

I wanted the five agents to be recognizable at a glance without the page turning into a rainbow. Each agent gets three things that never change:

- **An icon that says what they do**: a crown for the Boss who coordinates, a box for Inventory, a calculator for Accounting, a storefront for Facilities, and a speech bubble for Customer Service.
- **One muted color**, used only on that agent's avatar, its label, and the thread line beside its work. The colors are deliberately desaturated (navy, forest, ochre, plum, and rose) so all five can sit together calmly. They use the same hues as the agent colors on the Problem 6 planning page, so both views feel like one system.
- **A short role description** in the team strip at the top, so a first-time viewer learns who's who before reading any activity.

What makes this feel like a *team* rather than five chatbots is that the interface shows the connections between them, not only their individual messages.

- **The roster.** Five seats sit across the top of the workspace. Agents who took part light up, and agents who weren't needed fade back, so you can see at once that Facilities sat out a hoodie order. While a run is live, the agent currently working gets a soft pulsing ring.
- **"How the work moved."** This row summarizes every handoff as a little arrow chip: *Boss → Inventory*, *Inventory → Accounting*, *Boss → Accounting ×2*. It's the shape of the collaboration in one line. When Inventory goes straight to Accounting without asking the Boss, you can see it, and that's the full connectivity we built in Problem 5 made visible.
- **The step-by-step timeline** tells the run as a story. A handoff reads "Inventory → *Accounting*," with the actual question quoted underneath in that agent's color. An answer reads "Accounting reported back to *Inventory*." Tool calls are written as actions, like "Inventory checked stock and price," with a one-line plain summary of what came back ("Classic Bulldog Tee: S: 0 on hand · cost $8.00 · list $28.00"). The raw tool output is still available behind a "details" link for anyone who wants to check it. Steps are indented by delegation depth, so a question asked inside another question visibly nests.

The timeline reads the backend's audit trail directly, the same records written in Problem 5. I didn't create a second, friendlier set of activity messages for the frontend. Every sentence is a rewording of a real record, which means the story on screen can't drift from what actually happened.

## Telling the truth about status

This was the part I cared most about getting right. It's easy for a dashboard to imply success: the agents finish, a green check appears, and everyone assumes the problem is handled. At Campus Customs, finishing the analysis and resolving the ticket are different things. A ticket that needs a $2,400 rent payment isn't resolved until a human approves it and the payment is recorded.

So the status on each ticket is built from two separate facts. One is the ticket's status in the shop's records, which only says "resolved" when it really is. The other is the decision from the agents' latest run.

- **Resolved** is green, and it is the only status that gets a diagonal "Resolved" ribbon across the corner and a softly green-tinted card. That treatment is reserved for tickets that are closed in the shop's records, so it actually means something.
- **Waiting on approval** is amber, with a line underneath like "1 decision waiting for you. Still open."
- **Blocked** is a muted red: something outside the team's control has to happen first.
- **Needs information** is slate blue: the data needed to decide is missing.
- If the Boss judges a ticket resolved but the record hasn't caught up, the card says "Agents say resolved" and "Not yet closed in the shop's records," rather than claiming it's done.

Almost every unresolved status ends with the words "Still open." That's on purpose: it's a small, repeated reminder that analysis is not resolution. When a run finishes, the outcome card leads with the same honesty: "The agents finished their analysis, but the ticket is not resolved: 1 request needs your decision."

Completed work should still feel satisfying to review, so the outcome card is the most designed part of the workspace:
- the Boss's summary in a larger serif, like a pull quote;
- a "Who did what" grid with one card per agent, showing its own summary, who asked it for help, the tools it used, and anything it drafted or requested;
- drafted messages in expandable panels, each marked with a dashed **"Draft · not sent"** stamp, so there's never any doubt that nothing went out;
- next steps and open questions;
- the full evidence and reasoning, one click away rather than in the way.

## Why cash and approvals get so much room

Money is the one place where the agents' work turns into something that can't easily be undone, so it gets the most visible real estate on the page.

**The checking balance appears twice.** It's in the header on every screen, and again as a large figure at the top of the decision column. Next to it, the dashboard keeps two kinds of numbers clearly apart:

- **Actual:** the balance in the shop's cash account. The label says where it comes from and that it only changes when an approved payment is recorded.
- **Proposed:** a thin bar under the balance shows how much of it the pending payment requests would use, followed by "Proposed, not approved" and "If every proposal were approved."

That second number matters because the three tickets share one account. Rent and the overdue invoice together would leave $160, and the operator should see that before approving the first one, not after. Those projected figures come from the backend previewing all pending payments through the MCP server. The frontend doesn't do its own math on money it doesn't own.

**Each approval request is written for a human, not a database.** A card tells you:
- what kind of request it is;
- which ticket it came from;
- which agent recommended it, with their avatar;
- who gets paid and when it's due;
- the amount, in large type;
- the balance before and after: "$3,400.00 → $1,000.00."

Payment requests have a warm amber tint. Requests that don't move money, like a price change, are plainly labeled "No money moves. Approving records your decision."

Approving takes two deliberate steps: open the review, then confirm with your name. The review screen lists the payee, what it's for, the amount, the balance now, and the balance after. It explains that the backend will check again before paying, that nothing has been paid already, the amount hasn't changed, and cash still covers it. After you approve, a confirmation appears, the balance in the header updates with a brief green glow, and the request moves to "Recently decided" with your name next to it.

The frontend never changes financial data itself. It asks the backend, the backend asks the MCP server, and only then does the database change.

## Small choices that make it feel like a workspace

- **It remembers your name.** Approvals ask who you are, and the desk remembers it for next time. Every decision in the audit trail is tied to a person, and you don't have to retype it.
- **Reset takes real friction.** Resetting the shop's data affects everything, so it lives in a quiet button in the corner. The dialog explains in plain terms what will and won't happen; most importantly, the audit history is kept. It only unlocks once you've typed your name and the word RESET. It also refuses while a run is in progress.
- **Waiting is designed for.** Agent runs take a minute or more. The page shows a live elapsed timer, pulsing avatars on whoever is working, and new steps appearing as they happen (it checks every second and a half during a run). You can browse other tickets while one runs.
- **Errors stay calm and specific.** If the backend is down, a single banner says so, gives the exact command to start it, and keeps retrying; the page recovers by itself when the backend returns. Rejected actions, like an attempt to pay something twice, appear as notices in plain language, with the backend's exact reason in parentheses.
- **The typography does the hierarchy.** A warm serif (Fraunces) carries the things you'd read aloud: ticket numbers, subjects, the balance, decisions. A clean sans-serif (Inter) carries everything you scan. Both fonts are bundled with the app, so it looks the same on any machine, even offline. The background is a warm paper tone instead of stark white, and color is mostly reserved for meaning. When something is amber, red, or green, it's telling you something.
- **The campus character is light.** A navy "CC" monogram, a collegiate serif, and a tone that reads like a well-run shop rather than a server console. There's enough personality to feel like Campus Customs, without the decoration getting in the way of the work.

## A sense of place

Campus Customs sells to a campus, so the desk should feel like it belongs in New Haven. Every Yale touch is original line art drawn for this project. None of them are official Yale marks, residential college crests, or logos, and I left out portraits of real people entirely, so the page never invents anyone's likeness. That keeps the repository safe to publish while still feeling like home.

- **The bulldog.** A friendly, hand-drawn bulldog (folded ears, heavy brow, the classic underbite) sits beside the "Today at the desk" headline as the shop's mascot. It reappears in the empty states, so "Nothing needs your sign-off" comes with a bulldog keeping watch instead of a generic checkmark.
- **Collegiate Gothic.** A faint tower with lancet windows and a spire rises behind the team strip, in the spirit of the campus's Gothic towers without copying any one building. A small quatrefoil, the four-lobed ornament carved into tracery, marks section headings and sits as a barely visible watermark in the corner of each ticket card. The page background is a whisper-light field of the same quatrefoils, like the texture of carved stone.
- **The Elm City.** An elm leaf drifts in the corner of the cash card, a nod to New Haven's nickname.
- **A skyline to close.** The footer is a line drawing of cloister arches, elms, and a tower, with a navy shop pennant and "New Haven, Connecticut."
- **Yale Blue.** The single accent color is Yale Blue (#00356B, from Yale's published brand colors). It's used for the ticket numbers, buttons, and every emblem, so the motifs and the interface read as one palette rather than decoration added on top.

All of these sit at low contrast and behind the content. They give the desk personality, but they never compete with a status, a balance, or an approval.

## What I chose not to do

There's no mock data anywhere in the app. Every ticket, step, number, and request comes from the FastAPI backend, which gets its shop data only from the MCP server. There are no charts for their own sake and no animations beyond the few that carry meaning: a pulse means "working," and a glow means "this number just changed." Some runs were recorded before outcomes were fully saved. For those, the dashboard says so plainly and shows what it does have, rather than reconstructing details it can't verify.
