"""Campus Customs backend: FastAPI routes for the React dashboard.

Start from the backend/ folder:
    uvicorn main:app --reload --port 8000

Shop data is read and changed only through the Campus Customs MCP server
(mcp_server/server.py), the same tools the agents use. The approve route is
the only place cash changes, and it is only called when a human clicks
Approve on the dashboard.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from pydantic import BaseModel, Field

import audit
from mcp_link import server_module
from reset_db import reset_db
from team import new_run_id, run_ticket

app = FastAPI(title="Campus Customs backend", version="1.0")

# The Vite dashboard (http://localhost:5173) calls these routes from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# One agent run at a time, so two tickets never race for the same cash.
_run_lock = asyncio.Lock()
_running_ticket: int | None = None
_runs: dict[str, dict[str, Any]] = {}  # run_id -> {ticket_id, status, decision, error}
_tasks: set[asyncio.Task] = set()

CLOSED_STATUSES = {"resolved", "declined"}


# ---------------------------------------------------------------- MCP helper


async def mcp_call(tool: str, **args: Any) -> Any:
    """Call one tool on the Campus Customs MCP server and return its result."""
    async with Client(server_module().mcp) as client:
        result = await client.call_tool(tool, args, raise_on_error=False)
    if result.is_error:
        text = " ".join(getattr(c, "text", "") for c in result.content)
        raise HTTPException(status_code=500, detail=f"MCP tool {tool} failed: {text}")
    data = result.structured_content
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


# ---------------------------------------------------------------- request bodies


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving.")
    note: str = ""


class RejectBody(BaseModel):
    decided_by: str = Field(min_length=1, description="Name of the human rejecting.")
    note: str = ""


# ---------------------------------------------------------------- routes


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "running_ticket": _running_ticket}


@app.get("/api/tickets")
async def list_tickets() -> list[dict]:
    """Every ticket with its status and whether it is open or resolved."""
    tickets = await mcp_call("list_tickets")
    for t in tickets:
        t["state"] = "resolved" if t["status"] in CLOSED_STATUSES else "open"
        t["running"] = t["id"] == _running_ticket
    return tickets


async def _close_ticket(ticket_id: int, outcome: str) -> None:
    """When the team finishes, mark the ticket resolved. Anything still waiting
    on a human stays on the board as its own pending item."""
    if outcome in ("resolved", "waiting_on_approval"):
        await mcp_call("update_ticket_status", ticket_id=ticket_id, status="resolved",
                       note=f"Agent run finished (Boss outcome: {outcome}). "
                            "Any approvals still pending are on the board.",
                       updated_by="desk")


async def _run_in_background(run_id: str, ticket_id: int) -> None:
    global _running_ticket
    async with _run_lock:
        _running_ticket = ticket_id
        try:
            decision = await run_ticket(ticket_id, run_id=run_id)
            await _close_ticket(ticket_id, decision.outcome)
            _runs[run_id].update(status="done", decision=decision.model_dump())
        except Exception as exc:
            _runs[run_id].update(status="error", error=f"{type(exc).__name__}: {exc}"[:500])
        finally:
            _running_ticket = None


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket_route(ticket_id: int) -> dict:
    """Start the agent team on one ticket. Returns a run_id right away; watch
    progress with /api/events?run_id=... and the result with /api/runs/{run_id}."""
    ticket = await mcp_call("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(status_code=404, detail=f"No ticket {ticket_id}.")
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail=f"Ticket {_running_ticket} is already running.")
    run_id = new_run_id()
    _runs[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running",
                     "started": audit.now(), "decision": None, "error": None}
    task = asyncio.create_task(_run_in_background(run_id, ticket_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return _runs[run_id]


@app.get("/api/runs/{run_id}")
async def run_status(run_id: str) -> dict:
    """Whether a run is still going, and the Boss's decision once it's done."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"No run {run_id} since the server started.")
    return _runs[run_id]


def _simplify(entry: dict) -> dict:
    """One audit step in a dashboard-friendly shape: who, what they said, which tools."""
    said = entry.get("text")
    if entry.get("step_type") == "final_answer":
        out = entry.get("output") or {}
        said = out.get("summary") if isinstance(out, dict) else out
    elif entry.get("step_type") == "task_received":
        said = entry.get("task")
    elif entry.get("step_type") == "error":
        said = entry.get("error")
    return {
        "time": entry.get("time"),
        "run_id": entry.get("run_id"),
        "ticket_id": entry.get("ticket_id"),
        "agent": entry.get("agent"),
        "chain": entry.get("chain", []),
        "step": entry.get("step"),
        "step_type": entry.get("step_type"),
        "said": said,
        "tools_called": entry.get("tool_calls", []),
        "tool_results": entry.get("tool_results", []),
        "output": entry.get("output") if entry.get("step_type") == "final_answer" else None,
    }


@app.get("/api/events")
async def recent_events(
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
    since_last_reset: bool = False,
) -> list[dict]:
    """Recent agent steps from output/audit_trail.json, oldest first."""
    if not audit.AUDIT_PATH.exists():
        return []
    try:
        rows = json.loads(audit.AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if since_last_reset:
        last = max((i for i, r in enumerate(rows) if r.get("step_type") == "reset"), default=-1)
        rows = rows[last + 1:]
    if ticket_id is not None:
        rows = [r for r in rows if r.get("ticket_id") == ticket_id]
    if run_id:
        rows = [r for r in rows if r.get("run_id") == run_id]
    return [_simplify(r) for r in rows[-limit:]]


@app.get("/api/board")
async def board(ticket_id: int | None = None, status: str | None = None) -> list[dict]:
    """Requests and drafts the agents prepared (payments, POs, discounts, messages)."""
    return await mcp_call("list_board_items", ticket_id=ticket_id, status=status)


@app.post("/api/board/{item_id}/approve")
async def approve(item_id: int, body: ApproveBody) -> dict:
    """A human approves a board item. For a payment or purchase order this is
    what actually pays: payments row added, checking balance lowered, invoice or
    lease updated. Refused (409) if cash would go negative or the vendor is blocked."""
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="Wait for the running ticket to finish.")
    result = await mcp_call("approve_board_item", item_id=item_id,
                            approved_by=body.approved_by, note=body.note)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("message"))
    return result


@app.post("/api/board/{item_id}/reject")
async def reject(item_id: int, body: RejectBody) -> dict:
    """A human rejects a board item. Nothing is paid or sent."""
    result = await mcp_call("reject_board_item", item_id=item_id,
                            decided_by=body.decided_by, note=body.note)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("message"))
    return result


@app.get("/api/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts, plus pending requests and payments made."""
    data = await mcp_call("get_cash_balance")
    checking = next((a for a in data["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(status_code=404, detail="No checking account in cash_accounts.")
    payments = await mcp_call("list_payments")
    return {
        "account": "checking",
        "balance": checking["balance"],
        "as_of": checking["date"],
        "pending_requests": data["pending_requests"],
        "pending_amount": data["pending_amount"],
        "balance_if_all_pending_approved": data["balance_if_all_pending_approved"],
        "payments": payments,
    }


@app.post("/api/reset")
async def reset() -> dict:
    """Copy data/campus_customs.db over data/campus_customs_new.db for a fresh run.
    The audit trail is kept (it is append-only)."""
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="Wait for the running ticket to finish.")
    path = reset_db()
    # Mark the reset in the audit trail so the dashboard knows older runs belong to a previous session.
    audit.append({"run_id": None, "ticket_id": None, "agent": None, "step_type": "reset",
                  "note": f"{path.name} reset from campus_customs.db"})
    tickets = await mcp_call("list_tickets")
    balance = (await mcp_call("get_cash_balance"))["total_balance"]
    return {"ok": True, "database": path.name, "tickets": len(tickets), "checking_balance": balance}
