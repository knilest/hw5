"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = (
    "boss", "inventory", "accounting", "facilities", "customer_service",
)


@dataclass
class TeamBudget:
    """Shared across every agent working one ticket, so delegation can't run away."""

    delegations: int = 0
    max_delegations: int = 8


@dataclass
class TeamDeps:
    """Passed to every agent run. `chain` is who asked whom, e.g. [boss, inventory]."""

    run_id: str
    ticket_id: int | None
    chain: list[AgentName]
    budget: TeamBudget = field(default_factory=TeamBudget)

    @property
    def me(self) -> AgentName:
        return self.chain[-1]

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


class AgentReport(BaseModel):
    """What a specialist (Inventory, Accounting, Facilities, Customer Service) hands back."""

    agent: AgentName
    summary: str = Field(description="Two or three sentences: what you found and what you did.")
    facts: list[str] = Field(
        default_factory=list,
        description="Each fact you relied on, with the MCP tool it came from, "
        "e.g. 'CC-TEE-WHITE size S qty 0 (check_stock)'.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Requests or drafts you put on the board. Empty if you only looked things up.",
    )
    board_item_ids: list[int] = Field(default_factory=list)
    needs_human: bool = Field(
        default=False, description="True if anything you prepared is waiting on human approval."
    )
    recommendation: str = Field(description="What you think the Boss should decide.")
    open_questions: list[str] = Field(default_factory=list)


class TicketDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    outcome: Literal["resolved", "waiting_on_approval", "declined", "needs_more_info"]
    summary: str = Field(description="Plain-language summary a shop manager can read in 20 seconds.")
    agents_consulted: list[AgentName] = Field(default_factory=list)
    board_item_ids: list[int] = Field(
        default_factory=list, description="Every board item created for this ticket."
    )
    human_actions_needed: list[str] = Field(
        default_factory=list,
        description="Exactly what a human must approve or decide, in the order they should do it.",
    )
    customer_message_drafted: bool = False
    rationale: str = Field(description="Why this is the right call, citing shop rules and numbers.")
