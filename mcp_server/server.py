"""Campus Customs MCP server — HW 5.

Gives the agent team tools for the shop database. Tools only return what is
in the database; they never make up data.

Database: ../data/campus_customs_new.db (the working copy).

Agents never move money directly. They put requests on the `board` table
(payments, purchase orders, discounts, customer message drafts). Only the
human-only tools (`approve_board_item`, `reject_board_item`) can approve a
request, and only an approved payment or purchase order changes cash.

Run from this folder (stdio):  python server.py
Run (HTTP):                    python server.py --http
HTTP URL:                      http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
HUMAN_ONLY_TOOLS = {"approve_board_item", "reject_board_item"}
TICKET_STATUSES = {"open", "in_progress", "waiting_on_approval", "resolved", "declined"}

BOARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS board (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    kind TEXT NOT NULL,          -- payment | purchase_order | discount | customer_message
    title TEXT NOT NULL,
    amount REAL,
    details TEXT NOT NULL,       -- JSON
    status TEXT NOT NULL,        -- pending | draft | approved | executed | rejected
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT
)
"""

mcp = FastMCP("campus-customs")


# ---------------------------------------------------------------- helpers


def _connect() -> sqlite3.Connection:
    """Open the working database. Fails instead of creating an empty file."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Copy data/campus_customs.db to "
            "data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute(BOARD_SCHEMA)
    return conn


def _today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' comes from desk.date_today, not the computer clock."""
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def _add_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    raise ValueError(iso_day)


def _invoice_view(row: sqlite3.Row, today: str) -> dict:
    inv = dict(row)
    days = _days_between(today, inv["due_date"])
    inv["days_until_due"] = days
    inv["overdue"] = inv["status"] == "open" and days < 0
    return inv


def _board_view(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["details"] = json.loads(item["details"])
    return item


def _check_requester(name: str) -> str | None:
    name = name.strip().lower()
    return name if name in AGENT_NAMES else None


def _open_invoices_for_vendor(conn: sqlite3.Connection, vendor_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM invoices WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
        (vendor_id,),
    ).fetchall()


def _add_board_item(conn, *, ticket_id, kind, title, amount, details, status, created_by) -> int:
    cur = conn.execute(
        "INSERT INTO board (ticket_id, kind, title, amount, details, status, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ticket_id, kind, title, amount, json.dumps(details), status, created_by, _now()),
    )
    return cur.lastrowid


def _active_duplicate(conn, kind: str, key: str, value) -> sqlite3.Row | None:
    """An earlier request for the same thing that is still waiting or done."""
    for row in conn.execute(
        "SELECT * FROM board WHERE kind = ? AND status IN ('pending', 'approved', 'executed')",
        (kind,),
    ).fetchall():
        if json.loads(row["details"]).get(key) == value:
            return row
    return None


# ---------------------------------------------------------------- read tools


@mcp.tool
def get_shop_today() -> dict:
    """Get the shop's 'today' (desk.date_today) and any desk notes.

    Always use this date for due-soon and overdue checks, never the real clock.
    """
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk").fetchone()
    return dict(row)


@mcp.tool
def list_tickets() -> list[dict]:
    """List every ticket (open and closed) with its status, oldest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket that is not resolved or declined, oldest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status NOT IN ('resolved', 'declined') "
            "ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with all of its fields.

    Linked fields: sku + size + qty point to inventory, lease_id to leases,
    invoice_id to invoices. Empty links are null.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        return {"found": False, "ticket_id": ticket_id, "message": "No ticket with this id."}
    return {"found": True, **dict(row)}


@mcp.tool
def check_stock(sku: str, size: str) -> dict:
    """Look up how many units of one SKU in one size are on the shelf.

    Use this before promising a customer an item. Size matters: the same
    SKU can be in stock in M but sold out in S. Sizes are S, M, L, XL,
    or OS (one size).
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? AND size = ?",
            (sku.strip().upper(), size.strip().upper()),
        ).fetchone()
    if row is None:
        return {"found": False, "sku": sku, "size": size,
                "message": "No inventory row for this SKU and size."}
    return {"found": True, **dict(row)}


@mcp.tool
def list_sizes_for_sku(sku: str) -> dict:
    """List stock for every size of one SKU (useful to offer a customer another size)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
            (sku.strip().upper(),),
        ).fetchall()
    if not rows:
        return {"found": False, "sku": sku, "message": "No inventory rows for this SKU."}
    return {"found": True, "sku": rows[0]["sku"], "name": rows[0]["name"],
            "sizes": [{"size": r["size"], "qty": r["qty"], "location": r["location"]} for r in rows]}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Get the unit cost and list price for one SKU, plus the margin.

    Use this to judge discount requests: any price above unit_cost still
    makes money on each unit; a price at or below unit_cost loses money.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku.strip().upper(),),
        ).fetchone()
    if row is None:
        return {"found": False, "sku": sku,
                "message": "No pricing row for this SKU."}
    p = dict(row)
    margin = p["list_price"] - p["unit_cost"]
    return {"found": True, **p,
            "margin_per_unit": round(margin, 2),
            "margin_pct_of_price": round(100 * margin / p["list_price"], 1)}


@mcp.tool
def list_vendors() -> list[dict]:
    """List all vendors with their specialty and lead time in days.

    Each vendor also shows whether it can ship right now: a vendor will not
    ship new product while it has any open (unpaid) invoice.
    """
    with _connect() as conn:
        vendors = [dict(r) for r in conn.execute("SELECT * FROM vendors ORDER BY id")]
        for v in vendors:
            open_ids = [r["id"] for r in _open_invoices_for_vendor(conn, v["id"])]
            v["open_invoice_ids"] = open_ids
            v["can_ship"] = not open_ids
    return vendors


@mcp.tool
def get_vendor_status(vendor_id: int) -> dict:
    """Get one vendor plus its open invoices and whether it will ship.

    can_ship is false while the vendor has any open invoice. If it can ship,
    earliest_arrival is shop today + lead_days.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if row is None:
            return {"found": False, "vendor_id": vendor_id, "message": "No vendor with this id."}
        today = _today(conn)
        open_invoices = [_invoice_view(r, today) for r in _open_invoices_for_vendor(conn, vendor_id)]
    vendor = dict(row)
    can_ship = not open_invoices
    arrival = (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat()
    return {"found": True, **vendor, "date_today": today,
            "open_invoices": open_invoices, "can_ship": can_ship,
            "earliest_arrival": arrival if can_ship else None,
            "blocked_reason": None if can_ship else
            "Vendor will not ship while it has an open unpaid invoice."}


@mcp.tool
def list_open_invoices() -> list[dict]:
    """List all open (unpaid) invoices with vendor name, days until due, and overdue flag."""
    with _connect() as conn:
        today = _today(conn)
        rows = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"
        ).fetchall()
    return [_invoice_view(r, today) for r in rows]


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Get one invoice with vendor name, days until due, and overdue flag."""
    with _connect() as conn:
        today = _today(conn)
        row = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
    if row is None:
        return {"found": False, "invoice_id": invoice_id, "message": "No invoice with this id."}
    return {"found": True, **_invoice_view(row, today)}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Get a shop lease: space, landlord, monthly rent, and next due date.

    Also returns the shop's today (desk.date_today) and how many days
    until rent is due, so the team can tell if rent is upcoming or overdue.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        today = _today(conn)
    if row is None:
        return {"found": False, "lease_id": lease_id,
                "message": "No lease with this id."}
    lease = dict(row)
    days = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days
    return {"found": True, **lease, "date_today": today,
            "days_until_due": days, "overdue": days < 0}


@mcp.tool
def get_cash_balance() -> dict:
    """Get every cash account balance, plus money already promised to
    pending payment and purchase-order requests on the board.

    No revenue comes in, so this is all the cash the shop will have.
    """
    with _connect() as conn:
        accounts = [dict(r) for r in conn.execute("SELECT * FROM cash_accounts")]
        pending = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n FROM board "
            "WHERE kind IN ('payment', 'purchase_order') AND status = 'pending'"
        ).fetchone()
    total = sum(a["balance"] for a in accounts)
    return {"accounts": accounts, "total_balance": total,
            "pending_requests": pending["n"], "pending_amount": pending["total"],
            "balance_if_all_pending_approved": round(total - pending["total"], 2)}


@mcp.tool
def list_payments() -> list[dict]:
    """List payments already made (each was approved by a human)."""
    with _connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id")]


@mcp.tool
def list_board_items(ticket_id: int | None = None, status: str | None = None) -> list[dict]:
    """List requests and drafts on the board, optionally for one ticket or one status.

    Statuses: pending, draft, approved, executed, rejected.
    """
    sql, args = "SELECT * FROM board WHERE 1=1", []
    if ticket_id is not None:
        sql += " AND ticket_id = ?"
        args.append(ticket_id)
    if status:
        sql += " AND status = ?"
        args.append(status)
    with _connect() as conn:
        return [_board_view(r) for r in conn.execute(sql + " ORDER BY id", args)]


# ---------------------------------------------------------------- agent write tools (board only)


@mcp.tool
def request_payment(
    pay_for: Literal["invoice", "rent"],
    ref_id: int,
    ticket_id: int,
    requested_by: str,
    reason: str,
) -> dict:
    """Ask a human to approve a payment. This does NOT pay anything.

    pay_for="invoice" with ref_id = invoices.id, or pay_for="rent" with
    ref_id = leases.id. The amount is read from the database, never typed in.
    The request waits on the board as 'pending' until a human approves it.
    """
    agent = _check_requester(requested_by)
    if agent is None:
        return {"ok": False, "message": f"requested_by must be one of {sorted(AGENT_NAMES)}."}
    with _connect() as conn:
        today = _today(conn)
        if pay_for == "invoice":
            row = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?", (ref_id,)
            ).fetchone()
            if row is None:
                return {"ok": False, "message": f"No invoice {ref_id}."}
            if row["status"] != "open":
                return {"ok": False, "message": f"Invoice {ref_id} is '{row['status']}', not open."}
            amount = row["amount"]
            payee = row["vendor_name"]
            details = {"pay_for": "invoice", "invoice_id": ref_id, "payee": payee,
                       "due_date": row["due_date"],
                       "overdue": _days_between(today, row["due_date"]) < 0}
            key = ("invoice_id", ref_id)
        else:
            row = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"ok": False, "message": f"No lease {ref_id}."}
            amount = row["monthly_rent"]
            payee = row["landlord"]
            details = {"pay_for": "rent", "lease_id": ref_id, "payee": payee,
                       "space_name": row["space_name"], "due_date": row["next_due"],
                       "overdue": _days_between(today, row["next_due"]) < 0}
            key = ("lease_due", f"{ref_id}:{row['next_due']}")
            details["lease_due"] = key[1]
        dup = _active_duplicate(conn, "payment", *key)
        if dup is not None:
            return {"ok": False, "duplicate": True, "existing_item": _board_view(dup),
                    "message": "A request for this payment already exists."}
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()["balance"]
        details.update(reason=reason, account="checking",
                       balance_now=balance, covered_by_cash=balance >= amount)
        item_id = _add_board_item(
            conn, ticket_id=ticket_id, kind="payment",
            title=f"Pay {payee} ${amount:,.2f} ({pay_for} {ref_id})",
            amount=amount, details=details, status="pending", created_by=agent,
        )
        conn.execute("UPDATE tickets SET status='waiting_on_approval' WHERE id=? AND status IN ('open','in_progress')", (ticket_id,))
        item = _board_view(conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone())
    return {"ok": True, "message": "Payment request is pending human approval. Nothing was paid.",
            "item": item}


@mcp.tool
def draft_purchase_order(
    ticket_id: int,
    vendor_id: int,
    sku: str,
    size: str,
    qty: int,
    requested_by: str,
    reason: str,
) -> dict:
    """Prepare a restock purchase order for human approval. Nothing is ordered yet.

    Cost = qty x unit_cost from pricing. If approved, the vendor is paid up
    front from checking. If the vendor has an open invoice, the PO is marked
    blocked and cannot be approved until that invoice is paid.
    """
    agent = _check_requester(requested_by)
    if agent is None:
        return {"ok": False, "message": f"requested_by must be one of {sorted(AGENT_NAMES)}."}
    if qty <= 0:
        return {"ok": False, "message": "qty must be at least 1."}
    sku, size = sku.strip().upper(), size.strip().upper()
    with _connect() as conn:
        today = _today(conn)
        vendor = conn.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"ok": False, "message": f"No vendor {vendor_id}."}
        inv = conn.execute("SELECT * FROM inventory WHERE sku=? AND size=?", (sku, size)).fetchone()
        if inv is None:
            return {"ok": False, "message": f"No inventory row for {sku} size {size}."}
        price = conn.execute("SELECT * FROM pricing WHERE sku=?", (sku,)).fetchone()
        if price is None:
            return {"ok": False, "message": f"No pricing for {sku}; cannot cost the order."}
        cost = round(qty * price["unit_cost"], 2)
        blocked_by = [r["id"] for r in _open_invoices_for_vendor(conn, vendor_id)]
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()["balance"]
        details = {
            "vendor_id": vendor_id, "vendor_name": vendor["name"],
            "vendor_specialty": vendor["specialty"], "lead_days": vendor["lead_days"],
            "sku": sku, "size": size, "item_name": inv["name"], "qty": qty,
            "unit_cost": price["unit_cost"], "qty_on_hand": inv["qty"],
            "blocked_by_open_invoices": blocked_by,
            "earliest_arrival_if_approved_today":
                (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat(),
            "reason": reason, "account": "checking",
            "balance_now": balance, "covered_by_cash": balance >= cost,
        }
        item_id = _add_board_item(
            conn, ticket_id=ticket_id, kind="purchase_order",
            title=f"PO: {qty} x {sku} {size} from {vendor['name']} (${cost:,.2f})",
            amount=cost, details=details, status="pending", created_by=agent,
        )
        conn.execute("UPDATE tickets SET status='waiting_on_approval' WHERE id=? AND status IN ('open','in_progress')", (ticket_id,))
        item = _board_view(conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone())
    msg = "Purchase order is pending human approval."
    if blocked_by:
        msg += f" BLOCKED: vendor has open invoice(s) {blocked_by}; pay them first."
    return {"ok": True, "message": msg, "item": item}


@mcp.tool
def propose_discount(
    ticket_id: int,
    sku: str,
    qty: int,
    unit_price: float,
    requested_by: str,
    reason: str,
) -> dict:
    """Propose a discounted unit price for human approval.

    Refused if unit_price is at or below unit_cost (the shop would lose
    money) or above list_price (not a discount).
    """
    agent = _check_requester(requested_by)
    if agent is None:
        return {"ok": False, "message": f"requested_by must be one of {sorted(AGENT_NAMES)}."}
    sku = sku.strip().upper()
    with _connect() as conn:
        price = conn.execute("SELECT * FROM pricing WHERE sku=?", (sku,)).fetchone()
        if price is None:
            return {"ok": False, "message": f"No pricing for {sku}."}
        if unit_price <= price["unit_cost"]:
            return {"ok": False, "message": f"Refused: ${unit_price:.2f} is at or below unit cost ${price['unit_cost']:.2f}."}
        if unit_price > price["list_price"]:
            return {"ok": False, "message": f"Refused: ${unit_price:.2f} is above list price ${price['list_price']:.2f}."}
        discount_pct = round(100 * (1 - unit_price / price["list_price"]), 1)
        details = {
            "sku": sku, "qty": qty, "unit_price": unit_price,
            "list_price": price["list_price"], "unit_cost": price["unit_cost"],
            "discount_pct": discount_pct,
            "margin_per_unit": round(unit_price - price["unit_cost"], 2),
            "order_revenue": round(qty * unit_price, 2),
            "order_profit": round(qty * (unit_price - price["unit_cost"]), 2),
            "reason": reason,
        }
        item_id = _add_board_item(
            conn, ticket_id=ticket_id, kind="discount",
            title=f"Discount: {qty} x {sku} at ${unit_price:.2f} ({discount_pct}% off)",
            amount=None, details=details, status="pending", created_by=agent,
        )
        conn.execute("UPDATE tickets SET status='waiting_on_approval' WHERE id=? AND status IN ('open','in_progress')", (ticket_id,))
        item = _board_view(conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone())
    return {"ok": True, "message": "Discount is pending human approval.", "item": item}


@mcp.tool
def draft_customer_message(
    ticket_id: int,
    to: str,
    subject: str,
    body: str,
    written_by: str,
) -> dict:
    """Save a draft message to a customer on the board. It is NEVER sent.

    A human reviews drafts on the dashboard; nothing is emailed.
    """
    agent = _check_requester(written_by)
    if agent is None:
        return {"ok": False, "message": f"written_by must be one of {sorted(AGENT_NAMES)}."}
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id=?", (ticket_id,)).fetchone() is None:
            return {"ok": False, "message": f"No ticket {ticket_id}."}
        item_id = _add_board_item(
            conn, ticket_id=ticket_id, kind="customer_message",
            title=f"Draft to {to}: {subject}", amount=None,
            details={"to": to, "subject": subject, "body": body},
            status="draft", created_by=agent,
        )
        item = _board_view(conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone())
    return {"ok": True, "message": "Draft saved on the board. It was not sent.", "item": item}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str, updated_by: str) -> dict:
    """Set a ticket's status and append a dated note.

    Statuses: open, in_progress, waiting_on_approval, resolved, declined.
    """
    agent = _check_requester(updated_by)
    if updated_by.strip().lower() == "desk":  # the dashboard backend closing a finished run
        agent = "desk"
    if agent is None:
        return {"ok": False, "message": f"updated_by must be one of {sorted(AGENT_NAMES)}."}
    if status not in TICKET_STATUSES:
        return {"ok": False, "message": f"status must be one of {sorted(TICKET_STATUSES)}."}
    with _connect() as conn:
        row = conn.execute("SELECT notes FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            return {"ok": False, "message": f"No ticket {ticket_id}."}
        today = _today(conn)
        notes = (row["notes"] or "") + f"\n[{today} {agent}] {note}"
        conn.execute("UPDATE tickets SET status=?, notes=? WHERE id=?", (status, notes.strip(), ticket_id))
        ticket = dict(conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone())
    return {"ok": True, "ticket": ticket}


# ---------------------------------------------------------------- human-only tools
# The backend hides these from every agent. Only the dashboard calls them.


def _execute_money(conn: sqlite3.Connection, item: sqlite3.Row, approved_by: str) -> dict:
    """Pay an approved payment or purchase order. Refuses rather than go negative."""
    d = json.loads(item["details"])
    today = _today(conn)
    account = d.get("account", "checking")

    if item["kind"] == "payment" and d["pay_for"] == "invoice":
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (d["invoice_id"],)).fetchone()
        if inv is None or inv["status"] != "open":
            return {"ok": False, "message": f"Invoice {d['invoice_id']} is no longer open."}
        amount, kind, ref_id = inv["amount"], "invoice", inv["id"]
    elif item["kind"] == "payment":
        lease = conn.execute("SELECT * FROM leases WHERE id=?", (d["lease_id"],)).fetchone()
        if lease is None or f"{lease['id']}:{lease['next_due']}" != d["lease_due"]:
            return {"ok": False, "message": "That rent period was already paid."}
        amount, kind, ref_id = lease["monthly_rent"], "rent", lease["id"]
    else:  # purchase_order
        blocked = [r["id"] for r in _open_invoices_for_vendor(conn, d["vendor_id"])]
        if blocked:
            return {"ok": False, "message": f"Refused: {d['vendor_name']} has open invoice(s) {blocked} and will not ship."}
        amount, kind, ref_id = item["amount"], "purchase_order", item["id"]

    acct = conn.execute("SELECT * FROM cash_accounts WHERE name=?", (account,)).fetchone()
    if acct is None:
        return {"ok": False, "message": f"No cash account '{account}'."}
    if acct["balance"] < amount:
        return {"ok": False, "message":
                f"Refused: {account} has ${acct['balance']:,.2f}, payment needs ${amount:,.2f}. "
                "No negative balances."}

    new_balance = round(acct["balance"] - amount, 2)
    conn.execute("UPDATE cash_accounts SET balance=?, date=? WHERE name=?", (new_balance, today, account))
    cur = conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?,?,?,?,?,?)",
        (kind, ref_id, amount, account, today, approved_by),
    )
    if kind == "invoice":
        conn.execute("UPDATE invoices SET status='paid' WHERE id=?", (ref_id,))
    elif kind == "rent":
        conn.execute("UPDATE leases SET next_due=? WHERE id=?", (_add_month(d["due_date"]), ref_id))
    return {"ok": True, "payment_id": cur.lastrowid, "amount": amount,
            "account": account, "new_balance": new_balance, "paid_at": today}


@mcp.tool
def approve_board_item(item_id: int, approved_by: str, note: str = "") -> dict:
    """HUMAN ONLY. Approve a board item. Payments and purchase orders are paid
    now (payments, cash_accounts, and invoices or leases are updated); if cash
    is short the payment is refused and the item stays pending.
    """
    who = approved_by.strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"ok": False, "message": "approved_by must be a human's name, not an agent."}
    with _connect() as conn:
        item = conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone()
        if item is None:
            return {"ok": False, "message": f"No board item {item_id}."}
        if item["status"] not in ("pending", "draft"):
            return {"ok": False, "message": f"Item {item_id} is already '{item['status']}'."}
        result = {"ok": True}
        new_status = "approved"
        if item["kind"] in ("payment", "purchase_order"):
            result = _execute_money(conn, item, who)
            if not result["ok"]:
                return {**result, "item": _board_view(item)}
            new_status = "executed"
        conn.execute(
            "UPDATE board SET status=?, decided_by=?, decided_at=?, decision_note=? WHERE id=?",
            (new_status, who, _now(), note, item_id),
        )
        updated = _board_view(conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone())
    return {**result, "item": updated}


@mcp.tool
def reject_board_item(item_id: int, decided_by: str, note: str = "") -> dict:
    """HUMAN ONLY. Reject a pending request or draft. Nothing is paid or sent."""
    who = decided_by.strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"ok": False, "message": "decided_by must be a human's name, not an agent."}
    with _connect() as conn:
        item = conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone()
        if item is None:
            return {"ok": False, "message": f"No board item {item_id}."}
        if item["status"] not in ("pending", "draft"):
            return {"ok": False, "message": f"Item {item_id} is already '{item['status']}'."}
        conn.execute(
            "UPDATE board SET status='rejected', decided_by=?, decided_at=?, decision_note=? WHERE id=?",
            (who, _now(), note, item_id),
        )
        updated = _board_view(conn.execute("SELECT * FROM board WHERE id=?", (item_id,)).fetchone())
    return {"ok": True, "item": updated}


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs MCP server")
    parser.add_argument("--http", action="store_true", help="serve over HTTP")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
