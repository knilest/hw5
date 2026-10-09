"""Inventory: checks stock by SKU and size, spots shortfalls, finds a vendor to restock."""

from models import AgentReport

NAME = "inventory"
TITLE = "Inventory"
DESCRIPTION = ("Checks stock by SKU and size, spots shortfalls, and figures out which "
               "vendor can restock and when.")
PROMPT_FILE = "inventory.md"
OUTPUT_TYPE = AgentReport
MCP_TOOLS = frozenset({
    "get_shop_today",
    "get_ticket",
    "check_stock",
    "list_sizes_for_sku",
    "get_pricing",
    "list_vendors",
    "get_vendor_status",
})
