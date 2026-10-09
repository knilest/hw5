"""Customer Service: drafts messages for customers. Drafts stay on the board; nothing is sent."""

from models import AgentReport

NAME = "customer_service"
TITLE = "Customer Service"
DESCRIPTION = "Drafts messages to customers (saved on the board, never sent)."
PROMPT_FILE = "customer_service.md"
OUTPUT_TYPE = AgentReport
MCP_TOOLS = frozenset({
    "get_shop_today",
    "get_ticket",
    "check_stock",
    "list_sizes_for_sku",
    "get_pricing",
    "list_board_items",
    "draft_customer_message",
})
