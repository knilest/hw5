"""The Campus Customs agent team: five PydanticAI agents with full connectivity.

Every agent has an `ask_teammate` tool that can hand a task to any other
agent. Each agent loop is stepped through with `agent.iter()` so every step
(model call, tool calls, tool results, final answer) is appended to
output/audit_trail.json as it happens.

Loop guards (to keep token use in check):
- an agent can't ask itself or anyone already up the chain (no ping-pong)
- at most MAX_DEPTH hand-offs deep and MAX_DELEGATIONS hand-offs per ticket
- one shared UsageLimits budget per ticket across every agent
"""

from __future__ import annotations

import os
import uuid
from typing import Any

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, RunContext, Tool, UserPromptNode  # noqa: E402
from pydantic_ai.messages import (  # noqa: E402
    BaseToolCallPart,
    BaseToolReturnPart,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
)
from pydantic_ai.usage import RunUsage, UsageLimits  # noqa: E402
from pydantic_graph import End  # noqa: E402

import audit  # noqa: E402
from agents import ROLES  # noqa: E402
from llm import MODEL_NAME, get_model  # noqa: E402
from mcp_link import server_module, toolset_for  # noqa: E402
from models import AGENT_NAMES, AgentName, TeamBudget, TeamDeps, TicketDecision  # noqa: E402
from pathlib import Path  # noqa: E402

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

MAX_DEPTH = 3
MAX_DELEGATIONS = 8
TICKET_LIMITS = UsageLimits(request_limit=40, tool_calls_limit=60, total_tokens_limit=400_000)

_agents: dict[str, Agent] = {}


# ---------------------------------------------------------------- building the team


def _roster_text(me: str) -> str:
    lines = [f"- `{name}` ({role.TITLE}): {role.DESCRIPTION}"
             for name, role in ROLES.items() if name != me]
    return (
        "\n\n## Your teammates\n"
        "You can hand any task to any teammate with the `ask_teammate` tool. "
        "Give them a specific, self-contained request (ticket id, SKU, size, qty, "
        "what you need back). They answer with a report.\n"
        + "\n".join(lines)
        + f"\n\nYour own agent name (use it for requested_by / written_by / updated_by) is `{me}`."
    )


async def ask_teammate(ctx: RunContext[TeamDeps], teammate: AgentName, request: str) -> dict:
    """Hand a task to another agent on the team and get their report back.

    Args:
        teammate: who should do it: boss, inventory, accounting, facilities, or customer_service.
        request: a specific, self-contained task, including the ticket id and the facts they need.
    """
    deps = ctx.deps
    if teammate == deps.me:
        return {"refused": "You can't delegate to yourself. Do it with your own tools."}
    if teammate in deps.chain:
        return {"refused": f"{teammate} is already waiting on you (chain: {' -> '.join(deps.chain)}). "
                           "Finish your part and report back instead."}
    if deps.depth + 1 > MAX_DEPTH:
        return {"refused": f"Hand-off limit reached ({MAX_DEPTH} deep). Finish with what you have."}
    if deps.budget.delegations >= deps.budget.max_delegations:
        return {"refused": f"This ticket already used {deps.budget.max_delegations} hand-offs. "
                           "Finish with what you have."}
    deps.budget.delegations += 1
    child = TeamDeps(run_id=deps.run_id, ticket_id=deps.ticket_id,
                     chain=[*deps.chain, teammate], budget=deps.budget)
    try:
        output = await run_agent(teammate, request, child, usage=ctx.usage)
    except Exception as exc:  # report the failure back instead of crashing the caller
        return {"error": f"{teammate} failed: {type(exc).__name__}: {exc}"[:400]}
    return output.model_dump()


def get_agent(name: str) -> Agent:
    if name not in _agents:
        role = ROLES[name]
        prompt = (PROMPTS_DIR / role.PROMPT_FILE).read_text(encoding="utf-8")
        _agents[name] = Agent(
            get_model(),
            name=name,
            deps_type=TeamDeps,
            output_type=role.OUTPUT_TYPE,
            instructions=prompt + _roster_text(name),
            toolsets=[toolset_for(role.MCP_TOOLS)],
            tools=[Tool(ask_teammate, takes_ctx=True)],
            retries=2,
        )
    return _agents[name]


# ---------------------------------------------------------------- audit of each loop step


def _describe(node: Any) -> dict[str, Any]:
    """Turn one agent-loop node into an audit record."""
    if isinstance(node, UserPromptNode):
        return {"step_type": "task_received", "task": audit.preview(node.user_prompt)}
    if isinstance(node, ModelRequestNode):
        results, retries = [], []
        for part in node.request.parts:
            if isinstance(part, BaseToolReturnPart):
                results.append({"tool": part.tool_name, "call_id": part.tool_call_id,
                                "result": audit.preview(part.content)})
            elif isinstance(part, RetryPromptPart):
                retries.append({"tool": part.tool_name, "problem": audit.preview(part.content)})
        return {"step_type": "model_request", "tool_results": results, "retries": retries}
    if isinstance(node, CallToolsNode):
        resp = node.model_response
        calls = [{"tool": p.tool_name, "call_id": p.tool_call_id, "args": p.args_as_dict()}
                 for p in resp.parts if isinstance(p, BaseToolCallPart)]
        text = [p.content for p in resp.parts if isinstance(p, TextPart) and p.content]
        thinking = [p.content for p in resp.parts if isinstance(p, ThinkingPart) and p.content]
        return {"step_type": "model_response", "tool_calls": calls,
                "text": audit.preview(" ".join(text)) if text else None,
                "thinking": audit.preview(" ".join(thinking)) if thinking else None,
                "provider_model_name": resp.model_name,
                "tokens": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}}
    if isinstance(node, End):
        out = node.data.output
        return {"step_type": "final_answer",
                "output": out.model_dump() if hasattr(out, "model_dump") else audit.preview(out)}
    return {"step_type": type(node).__name__}


async def run_agent(name: AgentName, task: str, deps: TeamDeps, usage: RunUsage | None = None):
    """Run one agent's loop, appending an audit entry for every step."""
    agent = get_agent(name)
    base = {"run_id": deps.run_id, "ticket_id": deps.ticket_id, "agent": name,
            "chain": list(deps.chain), "depth": deps.depth, "model": MODEL_NAME}
    step = 0
    try:
        async with agent.iter(task, deps=deps, usage=usage, usage_limits=TICKET_LIMITS) as run:
            async for node in run:
                step += 1
                audit.append({**base, "step": step, **_describe(node),
                              "ticket_usage_so_far": {"requests": run.usage.requests,
                                                      "total_tokens": run.usage.total_tokens}})
            return run.result.output
    except Exception as exc:
        audit.append({**base, "step": step + 1, "step_type": "error",
                      "error": f"{type(exc).__name__}: {exc}"[:600]})
        raise


# ---------------------------------------------------------------- entry points


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def run_ticket(ticket_id: int, run_id: str | None = None) -> TicketDecision:
    """Give one ticket to the Boss, who pulls in whichever teammates it needs."""
    deps = TeamDeps(run_id=run_id or new_run_id(), ticket_id=ticket_id, chain=["boss"],
                    budget=TeamBudget(max_delegations=MAX_DELEGATIONS))
    task = (f"Work ticket {ticket_id}. Read it with get_ticket, bring in the right teammates, "
            "and make the final call. Use only facts from the MCP tools.")
    return await run_agent("boss", task, deps)


async def open_ticket_ids() -> list[int]:
    """Ticket ids still open, read through the MCP server."""
    from fastmcp import Client
    async with Client(server_module().mcp) as client:
        result = await client.call_tool("list_open_tickets", {})
    rows = result.structured_content["result"]
    return [row["id"] for row in rows]


def human_only_tools() -> set[str]:
    return set(server_module().HUMAN_ONLY_TOOLS)


assert set(ROLES) == set(AGENT_NAMES), "every role needs an agent file"
