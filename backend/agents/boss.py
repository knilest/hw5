"""Boss: reads each ticket, decides who works on it, and makes the final call."""

from models import TicketDecision

NAME = "boss"
TITLE = "Boss"
DESCRIPTION = "Reads each ticket, decides who should work on it, and makes the final call."
PROMPT_FILE = "boss.md"
OUTPUT_TYPE = TicketDecision
MCP_TOOLS = frozenset({
    "get_shop_today",
    "list_open_tickets",
    "get_ticket",
    "get_cash_balance",
    "list_board_items",
    "update_ticket_status",
})
