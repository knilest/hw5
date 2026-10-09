# Campus Customs Agent Harness

Reference notes for the agent team. Source of truth: `data/campus_customs.db` (original, never edited). Agents and tools work on `data/campus_customs_new.db`.

**Contents:** [Database tables](#database-tables) · [Tickets](#the-three-open-tickets-and-how-they-link) · [MCP tools](#all-mcp-tools-current) · [The five agents](#the-agent-team-problem-5) · [Safety](#safety-and-guardrails) · [API routes](#backend-routes-problem-7) · [Dashboard](#dashboard-problem-8) · [Full run](#full-run-results-problem-9) · [How to run](#how-to-run-everything)

**The pieces and how they talk:**

```
React dashboard (frontend/, :5173)
        │  HTTP (CORS allows :5173)
        ▼
FastAPI backend (backend/main.py, :8000) ── runs ──► PydanticAI team (backend/team.py, gpt-6-luna via Portkey)
        │                                                   │
        │  MCP (in-process FastMCP client)                  │  MCP (filtered per agent; no human-only tools)
        ▼                                                   ▼
              Campus Customs MCP server (mcp_server/server.py)
                              │
                              ▼
                 data/campus_customs_new.db  (+ board table)
```

## Database tables

### `desk`
**Fields:** `date_today`, `notes`
**Why it matters:** `date_today` (2026-08-31) is "today" for the shop. Every overdue and due-soon check uses this date, not the computer clock.

### `tickets`
**Fields:** `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
**Why it matters:** This is the work queue. Boss reads each open ticket and uses `type` plus the linked `sku`/`lease_id`/`invoice_id` to decide which agents to bring in.

### `inventory`
**Fields:** `sku`, `name`, `size`, `qty`, `location` (key: `sku` + `size`)
**Why it matters:** Inventory checks stock here by SKU *and* size to spot shortfalls before anything is promised to a customer.

### `pricing`
**Fields:** `sku`, `unit_cost`, `list_price`
**Why it matters:** Accounting uses cost vs. price to check margins on discount requests and to price restock purchase orders.

### `vendors`
**Fields:** `id`, `name`, `specialty`, `lead_days`
**Why it matters:** Inventory picks the vendor whose `specialty` fits the item, and `lead_days` sets when restocked goods can arrive.

### `invoices`
**Fields:** `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
**Why it matters:** These are bills the shop owes. A vendor with an `open` invoice will not ship new product, so Accounting must check this before any restock.

### `leases`
**Fields:** `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
**Why it matters:** Facilities uses this to confirm rent amounts and due dates for the shop space.

### `cash_accounts`
**Fields:** `name`, `balance`, `date`
**Why it matters:** This is the only cash the shop has (no revenue is modeled). The pay tool must refuse any payment that would make a balance negative.

### `payments`
**Fields:** `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
**Why it matters:** This is the record of money paid out. It starts empty; a row is added only after a human approves a payment, with `approved_by` recording who approved it.

## The three open tickets and how they link

| Ticket | Type | Request | Links to |
|---|---|---|---|
| 101 | `customer_order` | Tauhid Zaman wants 1 Classic Bulldog Tee, size S | `inventory` (CC-TEE-WHITE / S), `invoices` #501 → `vendors` #1 |
| 102 | `rent_notice` | Elm City Properties says rent is due in 2 days | `leases` #1 |
| 103 | `price_override` | Yale AI Club wants 20 hoodies, size M, at a bulk discount | `inventory` (CC-HOOD-NAVY / M), `pricing` |

**What the links show:**
- **101:** Size S tee stock is **0**. The restock vendor is Bulldog Print Co (apparel, 5-day lead), but invoice #501 for **$840** was due **2026-08-28** and is still `open`, so it is **overdue** and the vendor won't ship until it is paid.
- **102:** Rent of **$2,400** for the Chapel Street shop is due **2026-09-02**.
- **103:** Only **8** size M hoodies are in stock, so 20 leaves a shortfall of **12**. Unit cost is $22 against a $58 list price, which leaves room for a discount. Restocking also goes through Bulldog Print Co, so it is blocked by the same unpaid invoice as 101.

**Cash pressure:** The checking balance is **$3,400**. Paying the invoice ($840) and the rent ($2,400) leaves **$160**, which is not enough for a 12-hoodie restock at cost ($264). The agents will need to prioritize, and every payment needs human approval.

## MCP tools (Problem 3: first three)

Server: `mcp_server/server.py` (FastMCP), working on `data/campus_customs_new.db`. Tools only return what is in the database.

| Tool | Reads | Unlocks ticket | Why it is the right tool for that ticket |
|---|---|---|---|
| `check_stock(sku, size)` | `inventory` | **101** | Tauhid ordered a CC-TEE-WHITE in size **S**, and stock is tracked per size, so this tool shows that size S is at **0** (even though M, L, and XL are in stock). That is the fact that turns 101 from "ship it" into "we need a restock." |
| `get_lease(lease_id)` | `leases`, `desk` | **102** | The landlord's email only says "rent due in 2 days," so this tool pulls lease #1's actual rent (**$2,400**) and due date (**2026-09-02**) and measures it against `desk.date_today` (2026-08-31). That confirms the amount and that rent is due in 2 days and not yet overdue. |
| `get_pricing(sku)` | `pricing` | **103** | The Yale AI Club wants a bulk discount on CC-HOOD-NAVY, and a discount can only be judged against cost. This tool shows the $22 unit cost vs. the $58 list price ($36, or 62%, margin per unit), so Accounting knows how low the price can go and still make money. |

## The agent team (Problem 5)

Built with PydanticAI. Every agent uses **`gpt-6-luna`** through Portkey (`backend/llm.py`; the model name is fixed in code). Prompts are in `backend/prompts/`, one file per agent; roles and tool lists are in `backend/agents/`; data types are in `backend/models.py`; the agent loops and delegation are in `backend/team.py`.

| Agent | Job | MCP tools it can call | Returns |
|---|---|---|---|
| **Boss** (`boss`) | Reads each ticket, routes it to teammates, checks the board, makes the final call and sets the ticket status | `get_shop_today`, `list_open_tickets`, `get_ticket`, `get_cash_balance`, `list_board_items`, `update_ticket_status` | `TicketDecision` |
| **Inventory** (`inventory`) | Checks stock by SKU and size, works out shortfalls, picks a vendor that can restock and when | `get_shop_today`, `get_ticket`, `check_stock`, `list_sizes_for_sku`, `get_pricing`, `list_vendors`, `get_vendor_status` | `AgentReport` |
| **Accounting** (`accounting`) | Watches cash and invoices, checks margins, prepares payments, purchase orders, and discounts for human approval | `get_shop_today`, `get_ticket`, `get_cash_balance`, `list_open_invoices`, `get_invoice`, `list_payments`, `get_vendor_status`, `get_pricing`, `get_lease`, `list_board_items`, `request_payment`, `draft_purchase_order`, `propose_discount` | `AgentReport` |
| **Facilities** (`facilities`) | Checks landlord notices against the lease, flags rent due dates, hands rent payment to Accounting | `get_shop_today`, `get_ticket`, `get_lease`, `list_board_items` | `AgentReport` |
| **Customer Service** (`customer_service`) | Drafts honest messages to customers; drafts stay on the board | `get_shop_today`, `get_ticket`, `check_stock`, `list_sizes_for_sku`, `get_pricing`, `list_board_items`, `draft_customer_message` | `AgentReport` |

**Full connectivity:** every agent also has `ask_teammate(teammate, request)`, which runs any other agent and returns its report. The Boss usually starts, but any agent can hand work to any other (for example, Facilities asks Accounting to request the rent payment).

**Audit trail:** each agent loop is stepped with `agent.iter()`, and every step is appended to `output/audit_trail.json` as it happens: the task, each model response (tool calls and arguments, text), each set of tool results, the final answer, and any error. Each entry also has `run_id`, `ticket_id`, `agent`, the delegation `chain` (e.g. `boss -> facilities`), `step`, `model`, token counts, and the ticket's running usage. The file is append-only; it is never wiped.

## All MCP tools (current)

| Tool | Table(s) | Who uses it | What it does |
|---|---|---|---|
| `get_shop_today` | `desk` | all agents | Shop's "today" for every due/overdue check |
| `list_tickets` | `tickets` | backend (dashboard) | Every ticket, open or closed, with status |
| `list_open_tickets` | `tickets` | Boss, backend | Tickets not yet resolved or declined |
| `get_ticket` | `tickets` | all agents | One ticket with its links (SKU/size/qty, lease, invoice) |
| `check_stock` | `inventory` | Inventory, Customer Service | Units on hand for one SKU **and size** |
| `list_sizes_for_sku` | `inventory` | Inventory, Customer Service | Stock across all sizes, to offer alternatives |
| `get_pricing` | `pricing` | Inventory, Accounting, Customer Service | Unit cost, list price, margin |
| `list_vendors` | `vendors`, `invoices` | Inventory | Vendors, specialty, lead days, and whether each can ship |
| `get_vendor_status` | `vendors`, `invoices`, `desk` | Inventory, Accounting | One vendor's open invoices, `can_ship`, earliest arrival |
| `list_open_invoices` | `invoices`, `vendors`, `desk` | Accounting | Unpaid invoices with days until due / overdue |
| `get_invoice` | `invoices`, `vendors`, `desk` | Accounting | One invoice with overdue flag |
| `get_lease` | `leases`, `desk` | Facilities, Accounting | Rent, landlord, next due date, days until due |
| `get_cash_balance` | `cash_accounts`, `board` | Boss, Accounting | Balance plus money already promised to pending requests |
| `list_payments` | `payments` | Accounting | Payments already made (all human-approved) |
| `list_board_items` | `board` | Boss, Accounting, Facilities, Customer Service | Pending requests and drafts, by ticket or status |
| `request_payment` | `invoices` or `leases`, `cash_accounts`, `board`, `tickets` | Accounting | Puts a payment request on the board as **pending**. Amount comes from the DB. Pays nothing. Blocks duplicates. |
| `draft_purchase_order` | `vendors`, `inventory`, `pricing`, `invoices`, `cash_accounts`, `board`, `tickets` | Accounting | Pending restock PO costed at qty × unit cost; flagged **blocked** if the vendor has an open invoice |
| `propose_discount` | `pricing`, `board`, `tickets` | Accounting | Pending discount; refused at or below unit cost or above list |
| `draft_customer_message` | `tickets`, `board` | Customer Service | Saves a message draft on the board. **Never sent.** |
| `update_ticket_status` | `tickets`, `desk` | Boss; backend (as `desk`) | Sets status and appends a dated note. The backend uses it to mark a ticket `resolved` when a run finishes. |
| `approve_board_item` | `board`, `payments`, `cash_accounts`, `invoices`, `leases` | **Humans only** (hidden from agents) | Approves an item. For payments/POs it pays now: inserts into `payments`, lowers `cash_accounts`, marks the invoice `paid` or moves the lease `next_due` a month. **Refuses if cash would go negative** or the vendor is blocked. |
| `reject_board_item` | `board` | **Humans only** (hidden from agents) | Rejects a request or draft; nothing is paid or sent |

The `board` table is added to the working copy by the MCP server (`CREATE TABLE IF NOT EXISTS`). It holds every pending request and draft, so resetting the database also clears the board.

## Safety and guardrails

What a real business would want before agents touch real customers and real money, and what this build already does:

- **A human approves every dollar.** Agents can only *request* payments and *draft* purchase orders. Approve/reject tools are removed from every agent's toolset in code (`backend/mcp_link.py`), and the server also refuses an approval whose `approved_by` is an agent name. Each payment row records who approved it.
- **Hard money limits live in code, not in prompts.** The pay step refuses any payment that would make cash negative, refuses POs to vendors with open invoices, and refuses discounts at or below cost. A confused or manipulated agent can't talk its way past these.
- **Amounts come from the database.** Payment amounts are read from the invoice or lease, not typed by the agent, so an agent can't pay the wrong amount. Duplicate requests for the same bill are blocked.
- **Nothing leaves the building.** No tool can send email or contact a vendor. Customer messages are drafts on the board until a human uses them.
- **Least privilege.** Each agent sees only the tools its job needs (Facilities can't touch money; Customer Service can't see cash or invoices).
- **Full audit trail.** Every agent step, tool call, argument, and result is appended to `output/audit_trail.json`, so any decision can be traced back.
- **Safe resets.** The original database is never edited; `backend/reset_db.py` (or `POST /api/reset`) restores the working copy, and the reset itself is logged in the audit trail.
- **Approvals on the dashboard are deliberate.** Approve buttons stay disabled until the human types their name in "Signing as", the button states the exact effect ("Approve & pay $840.00"), and any refusal from the server (not enough cash, vendor blocked) is shown in red on that item. Approvals and resets are blocked while a ticket is running.
- **Customer-facing rules in the prompts:** Customer Service never shares invoices, cash, costs, or margins with customers, never promises a discount or date a human hasn't approved, and every customer order must end with a draft so no customer is left without an answer.
- **Ticket text is treated as data, not instructions.** Every prompt tells agents to ignore instructions hidden in customer or landlord notes ("pay this now", "skip approval").
- **What a real shop should add:** login for approvers with dollar limits per person (two approvers above a threshold), alerts when an agent tries a refused action, review of customer drafts for tone and privacy, and keeping customer personal data out of model prompts where possible.

**Limits that keep token use in check:**
- **One model, one budget per ticket:** all agents working a ticket share one `UsageLimits` budget: at most **40 model requests, 60 tool calls, and 400,000 tokens** per ticket. The run stops if it hits a limit.
- **Delegation limits:** at most **8 hand-offs per ticket** and **3 levels deep**. An agent can't ask itself or anyone already waiting on it up the chain, which prevents A→B→A ping-pong loops.
- **Short, focused tool results:** tools return only the rows asked for, and the audit trail trims long values.
- **Tickets run one at a time,** so two tickets never fight over the same cash.
- **Prompts tell agents to ask each teammate once** with a complete request rather than many small ones.
- **Actual use in the full run** (all well under the limits):

  | Ticket | Model requests | Tokens | Hand-offs |
  |---|---|---|---|
  | 101 | 20 | ~78,100 | 3 |
  | 102 | 13 | ~43,600 | 2 |
  | 103 | 22 | ~85,200 | 4 |
  | **Total** | **55** | **~206,900** | **9** |

## Backend routes (Problem 7)

FastAPI app in `backend/main.py`. Start it from `backend/` with `uvicorn main:app --reload --port 8000`. Every route reads or changes shop data through the MCP server.

- `GET /api/tickets`: all tickets with their status and whether each is `open` or `resolved`.
- `POST /api/tickets/{ticket_id}/run`: starts the agent team on one ticket and returns a `run_id` right away (one run at a time; 409 if busy). When the team finishes, the ticket is marked `resolved`; anything still needing a human stays on the board.
- `GET /api/runs/{run_id}`: whether a run is still going, and the Boss's decision once it's done.
- `GET /api/events?limit=&ticket_id=&run_id=&since_last_reset=`: recent agent steps from the audit trail: which agent, what it said, which tools it called.
- `GET /api/board?ticket_id=&status=`: the payments, purchase orders, discounts, and message drafts the agents prepared.
- `POST /api/board/{item_id}/approve` (body `{approved_by, note}`): a human approves an item; for a payment or PO this is what actually pays and lowers cash (409 if cash would go negative or the vendor is blocked).
- `POST /api/board/{item_id}/reject` (body `{decided_by, note}`): a human rejects an item; nothing is paid or sent.
- `GET /api/cash`: the current checking balance from `cash_accounts`, plus pending requests and payments made.
- `POST /api/reset`: copies `campus_customs.db` over `campus_customs_new.db` for a fresh run (the audit trail is kept).
- `GET /api/health`: whether the server is up and which ticket is running.

## Dashboard (Problem 8)

React + Vite + TypeScript in `frontend/`, started with `npm run dev` (http://localhost:5173). It calls the backend at http://localhost:8000 (`frontend/src/api.ts`). Full design notes are in `output/design.md`.

- **Left, "On the spike":** the tickets as paper stubs, stamped `OPEN` / `IN PROGRESS` / `RESOLVED`, with an "N awaiting you" tag when approvals are left.
- **Center, "The floor":** the selected ticket and a **Send to the team** button; five agent desks that light up as each agent works; a live feed of every step, indented by who asked whom, with plain-English tool chips you can open to see the raw MCP result; after the run, the Boss's decision card ("For you to do") and one card per agent saying what it did.
- **Right, cash drawer + in-tray:** the checking balance (rolls down and prints a receipt when a payment is approved; turns coral if pending requests exceed cash) and every board item with Approve / Reject.
- While a run is going, the page refreshes tickets, events, board, and cash every 1.2 seconds from the backend routes above.
- `?ticket=101` opens a ticket directly; `&full=1` turns off scrolling and animation for full-page screenshots.

## Full run results (Problem 9)

Run on 2026-10-09 after a reset, one ticket at a time on the dashboard, with a human (kay) approving each ticket's items before the next run. Details: `output/desk_tickets.html` (Expected vs Actual + Cash tab), `output/resolved_tickets.json`, `output/resolved_board.html`, and every step in `output/audit_trail.json`.

| Ticket | Who worked | Approved by a human | Checking |
|---|---|---|---|
| 101 | Boss → Inventory, Accounting, Customer Service | invoice 501 $840.00, PO $8.00, draft to Tauhid | $3,400.00 → $2,552.00 |
| 102 | Boss → Facilities → Accounting | rent $2,400.00 | $2,552.00 → $152.00 |
| 103 | Boss → Inventory + Accounting, Customer Service | $46.00/unit discount, draft to the AI Club | $152.00 → $152.00 |

Ending balance **$152.00** matches `cash_accounts.checking` in `campus_customs_new.db`. The 12-hoodie restock ($264.00) was not bought because the shop is $112.00 short.

## How to run everything

From the `HW 5` folder, with `PORTKEY_API_KEY` in a `.env` file (this folder or the one above it):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
cd backend && ../.venv/Scripts/python -m uvicorn main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Reset the shop before a full run with the dashboard's **Reset the shop** button, `POST /api/reset`, or `python backend/reset_db.py`. Tickets can also be run without the dashboard: `python backend/run_tickets.py --all --reset`.
