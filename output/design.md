# The Desk: Dashboard Design

**What it is:** a React + Vite + TypeScript dashboard (`frontend/`) for watching the Campus Customs agent team work and signing off on what they prepare. Start it with `npm run dev` (backend on http://localhost:8000).

## The idea: a real shop desk, not a control panel

Most agent dashboards look like server monitors: dark screens, log lines, status codes. Campus Customs is a small campus shop, and the person using this is a shop manager, not an engineer. So the board is designed as the **front desk of a shop**: tickets on a spike, a floor where staff talk, a cash drawer, and an in-tray of things waiting for your signature. Every piece maps to something a manager already understands, so nobody has to learn what "board item status = pending" means.

The visual language follows the course's nonprofit style: warm paper background, a **thin serif** (Cormorant Garamond) for reading, and **forest green** as the main accent. A typewriter mono (IBM Plex Mono) is used only for money, SKUs, and small labels, the way numbers look on a ledger or receipt.

## Layout

Three columns, left to right, in the order your eye should move:

| Column | Name on screen | What it holds | Why here |
|---|---|---|---|
| Left | **On the spike** | The three tickets as paper stubs | You start by picking a ticket, like pulling a slip off a spike. |
| Center | **The floor** | The selected ticket, the five agent desks, the live conversation, and (after the run) the summary | This is where the work happens, so it gets the most space. |
| Right | **Cash drawer + In-tray** | The checking balance and everything waiting for approval | Money and approvals stay pinned in view (sticky) while you scroll the floor, because they're what a human has to act on. |

On a narrower screen, the cash drawer and in-tray move under the floor side by side; on a phone everything stacks.

## How the agents read differently

Each agent has its own **identity**, so you can tell who's talking without reading the name:

| Agent | Seal | Ink color | One-line job |
|---|---|---|---|
| The Boss | **B** | forest green | reads the ticket, makes the call |
| Inventory | **In** | slate blue | counts the shelves |
| Accounting | **Ac** | ochre / ledger gold | keeps the books |
| Facilities | **Fa** | brick red | minds the shop space |
| Customer Service | **CS** | plum | writes to customers |

- **Seals:** each agent has a round wax-seal monogram in its ink color. A seal is grey when the agent hasn't been called, gets a **spinning ring** while it's working, and turns solid when it has reported back.
- **Five desks across the floor:** the row of desks under the ticket is a live roster. The agent currently talking lifts slightly and fills with its tint ("speaking…"); the others say "at work", "reported back", or "not called". At a glance you can see the whole team's state, and which agents were *not* needed (useful for comparing with the plan in `desk_tickets.html`).
- **The conversation is indented by who asked whom.** A hand-off from the Boss to Inventory appears as a dotted line `THE BOSS ⟶ INVENTORY` with the Boss's actual request in quotes. Everything Inventory then does is indented one step under it, and if Facilities asks Accounting, Accounting is indented under Facilities. The delegation chain becomes visible as a shape, not something you have to reconstruct from logs.
- **Tool calls are chips in plain English** ("checked stock · CC-TEE-WHITE · S", "requested a payment · invoice · #501"). Clicking a chip opens it to show the real MCP tool name and the exact data it returned, so the friendly view never hides the evidence.
- **Reports back** are shaded cards in the agent's tint ("Accounting reports back to The Boss: …"), and the Boss's final call gets a green verdict panel.
- A **typing indicator** ("the team is working…") with bouncing dots shows the run is alive between steps.

## How resolved tickets show up

- Every ticket carries a **rubber stamp**: amber `OPEN`, a pulsing green `IN PROGRESS` while the team works, and a heavier `RESOLVED` stamp that **thumps down** (a quick scale-and-settle animation) when the run finishes. The backend marks the ticket resolved when the team is done; anything still needing a human stays in the in-tray, and the stub shows a small "2 awaiting you" tag so it isn't forgotten.
- When a run finishes, a **decision card** appears: the Boss's outcome, a 20-second summary, and a numbered **"For you to do"** list in the order to approve things, plus a collapsible **"Why"** with the Boss's reasoning.
- Below it, **"What each agent did"** shows one index card per agent with what it reported, what it put on the board, and the tools it used. Agents that weren't needed show as faded cards marked "Not called on this ticket", so a manager sees the routing at a glance.

## How cash shows up

- The **cash drawer** is the one dark-green panel on the page, so it reads as the most important number in the room. The balance is set large in a ledger mono.
- When a payment is approved, the balance **rolls down like an adding machine** (eased count from the old amount to the new one), a red **"−$840.00"** floats up and fades, and a **paper receipt** prints into the "Paid out" ledger below with a zig-zag torn edge, showing who approved it and on what shop date.
- A thin **gold meter** shows how much of today's cash is already promised to pending requests. If the pending requests add up to more than the shop has, the meter turns coral and a line warns: "That's $X more than we have." A footnote reminds the human that no revenue comes in, so cash only goes out.

## The in-tray: approvals designed to be safe

- Each item the agents prepared (payment, purchase order, discount, customer note) is a card with the seal of the agent that wrote it, the amount, and plain-language warnings pulled from the data: "Vendor won't ship until invoice 501 is paid", "Overdue since 2026-08-28", "Not enough cash when this was requested".
- The approve button says exactly what will happen ("**Approve & pay $840.00**", not just "OK"). Discount and message approvals say "Approve price" and "Approve draft", and drafts state that approving doesn't send anything.
- You must type your name in **"Signing as"** in the masthead before any approve button works, and that name is what gets written into `payments.approved_by`. Signing is deliberate, like signing a check.
- If the backend refuses (not enough cash, vendor still blocked), the refusal appears in red right on that card, so the human learns *why* instead of seeing a silent failure.
- Decided items get a rotated stamp (**PAID**, **APPROVED**, **REJECTED**) and sink below the open ones.

## Small touches that make it pleasant to sit at

- The shop's own date is set in italics in the masthead ("Monday, August 31, 2026"), taken from the database, so you always know what "today" means to the agents.
- The ticket card has faint ruled lines like a notepad, and the customer's note is set as a pull quote.
- Ticket stubs have a dotted perforation edge and slide out slightly when selected.
- Copy is written in a warm voice ("Quiet for now. Press *Send to the team*…", "Fresh start: the shop is back to its original books.") instead of system messages.
- The page retries quietly if the backend isn't up yet, and tells you the exact command to start it.
- **Reset the shop** asks for confirmation and explains that the audit trail is kept.
- All motion respects the operating system's "reduce motion" setting.

## How it talks to the backend

`frontend/src/api.ts` calls the FastAPI backend at **http://localhost:8000** (CORS in `backend/main.py` allows the Vite origin http://localhost:5173). Starting a run returns a `run_id` immediately; while it runs, the page refreshes tickets, events, board, and cash every 1.2 seconds, so new steps appear as the audit trail grows. It stops refreshing when the run finishes.
