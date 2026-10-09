"""Facilities: handles the shop space side (leases, rent, landlord notices)."""

from models import AgentReport

NAME = "facilities"
TITLE = "Facilities"
DESCRIPTION = "Handles the shop space: leases, rent due dates, and landlord notices."
PROMPT_FILE = "facilities.md"
OUTPUT_TYPE = AgentReport
MCP_TOOLS = frozenset({
    "get_shop_today",
    "get_ticket",
    "get_lease",
    "list_board_items",
})
