"""Accounting: watches cash and invoices, checks margins, prepares payments and POs for approval."""

from models import AgentReport

NAME = "accounting"
TITLE = "Accounting"
DESCRIPTION = ("Watches cash and invoices, checks margins and discounts, and prepares "
               "payments or purchase orders for human approval.")
PROMPT_FILE = "accounting.md"
OUTPUT_TYPE = AgentReport
MCP_TOOLS = frozenset({
    "get_shop_today",
    "get_ticket",
    "get_cash_balance",
    "list_open_invoices",
    "get_invoice",
    "list_payments",
    "get_vendor_status",
    "get_pricing",
    "get_lease",
    "list_board_items",
    "request_payment",
    "draft_purchase_order",
    "propose_discount",
})
