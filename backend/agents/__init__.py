"""The five Campus Customs agent roles. Each module says who the agent is,
which prompt file it reads, what it returns, and which MCP tools it may call."""

from agents import accounting, boss, customer_service, facilities, inventory

ROLES = {m.NAME: m for m in (boss, inventory, accounting, facilities, customer_service)}
