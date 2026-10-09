"""Connects the agents to the Campus Customs MCP server.

All shop facts and every database change go through mcp_server/server.py.
The server is attached in-process (same Python process, still spoken to over
the MCP protocol), so no separate terminal is needed. Each agent only sees
the MCP tools on its list, and no agent ever sees the human-only tools.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset

ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = ROOT / "mcp_server" / "server.py"

_server_module = None
_base: MCPToolset | None = None


def server_module():
    """Load mcp_server/server.py once."""
    global _server_module
    if _server_module is None:
        spec = importlib.util.spec_from_file_location("campus_customs_mcp", SERVER_PATH)
        _server_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_server_module)
    return _server_module


def base_toolset() -> MCPToolset:
    global _base
    if _base is None:
        _base = MCPToolset(server_module().mcp)
    return _base


def toolset_for(allowed: frozenset[str]) -> AbstractToolset:
    """The MCP tools one agent may call. Human-only tools are always removed."""
    human_only = server_module().HUMAN_ONLY_TOOLS
    leaked = allowed & human_only
    if leaked:
        raise ValueError(f"Agents may not be given human-only tools: {sorted(leaked)}")
    return base_toolset().filtered(lambda ctx, tool_def: tool_def.name in allowed)
