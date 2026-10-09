# Campus Customs MCP Server

This MCP server is the toolbox for the Campus Customs agent team. Every agent (Boss, Inventory, Accounting, Facilities, Customer Service) gets its facts about the shop, and makes every change, by calling these tools instead of guessing. The tools only return what is in the database and never make up data.

Built with [FastMCP](https://gofastmcp.com).

## Database

The server uses the working copy **`data/campus_customs_new.db`**. The original `data/campus_customs.db` is never touched; `backend/reset_db.py` copies it over the working copy to reset the shop.

The server adds one table to the working copy, **`board`**, which holds pending requests (payments, purchase orders, discounts) and customer message drafts until a human decides on them.

## Tools

**Read tools**

| Tool | Table(s) | What it does |
|---|---|---|
| `get_shop_today()` | `desk` | The shop's "today" (`desk.date_today`) for all due/overdue checks |
| `list_tickets()` | `tickets` | Every ticket, open or closed, with its status |
| `list_open_tickets()` | `tickets` | Tickets not yet resolved or declined |
| `get_ticket(ticket_id)` | `tickets` | One ticket with its linked SKU/size/qty, lease, and invoice |
| `check_stock(sku, size)` | `inventory` | Units on hand for one SKU in one size, plus the aisle |
| `list_sizes_for_sku(sku)` | `inventory` | Stock for every size of one SKU |
| `get_pricing(sku)` | `pricing` | Unit cost, list price, and margin per unit |
| `list_vendors()` | `vendors`, `invoices` | Vendors with specialty, lead days, and whether each can ship |
| `get_vendor_status(vendor_id)` | `vendors`, `invoices`, `desk` | One vendor's open invoices, `can_ship`, and earliest arrival |
| `list_open_invoices()` | `invoices`, `vendors`, `desk` | Unpaid invoices with days until due and overdue flag |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | One invoice with overdue flag |
| `get_lease(lease_id)` | `leases`, `desk` | Rent, landlord, next due date, and days until due |
| `get_cash_balance()` | `cash_accounts`, `board` | Cash balance plus money already promised to pending requests |
| `list_payments()` | `payments` | Payments already made |
| `list_board_items(ticket_id?, status?)` | `board` | Pending requests and drafts |

**Agent write tools** (these only put things on the board; they never move money or send anything)

| Tool | What it does |
|---|---|
| `request_payment(pay_for, ref_id, ticket_id, requested_by, reason)` | Pending payment request for an invoice or rent; amount is read from the DB; duplicates blocked |
| `draft_purchase_order(ticket_id, vendor_id, sku, size, qty, requested_by, reason)` | Pending restock PO costed at qty × unit cost; flagged blocked if the vendor has an open invoice |
| `propose_discount(ticket_id, sku, qty, unit_price, requested_by, reason)` | Pending discount; refused at or below unit cost or above list price |
| `draft_customer_message(ticket_id, to, subject, body, written_by)` | Saves a customer message draft; never sent |
| `update_ticket_status(ticket_id, status, note, updated_by)` | Sets a ticket's status and adds a dated note |

**Human-only tools** (hidden from every agent; for the approval dashboard)

| Tool | What it does |
|---|---|
| `approve_board_item(item_id, approved_by, note?)` | Approves an item. Payments and POs are paid now: a `payments` row is added, `cash_accounts` goes down, and the invoice is marked `paid` or the lease's `next_due` moves forward a month. Refuses if cash would go negative or the vendor still has an open invoice. |
| `reject_board_item(item_id, decided_by, note?)` | Rejects an item; nothing is paid or sent |

## Running

From the `HW 5` folder:

```bash
.venv/Scripts/python -m pip install -r mcp_server/requirements.txt
cd mcp_server
../.venv/Scripts/python server.py          # stdio
../.venv/Scripts/python server.py --http   # http://127.0.0.1:8001/mcp
```

The agent backend attaches this server in-process, so it does not need to be started separately for the agents.
