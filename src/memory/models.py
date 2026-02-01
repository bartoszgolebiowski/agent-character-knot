from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from src.tools.models import HelloWorldRequest
from src.engine.types import WorkflowStage


class ConstitutionalMemory(BaseModel):
    """The "agent's DNA." Security and ethical principles that the agent MUST NOT break. Guardrails."""


class WorkingMemory(BaseModel):
    """The context of the current session (RAM). What we're talking about "right now.\" """

    query_analysis: Optional[Any] = Field(
        default=None, description="Analysis and plan of the current query."
    )


class WorkflowTransition(BaseModel):
    """Record of a workflow stage transition."""

    from_stage: WorkflowStage
    to_stage: WorkflowStage
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: Optional[str] = None


class WorkflowMemory(BaseModel):
    """The State Machine. Where am I in the business process?"""

    current_stage: WorkflowStage = Field(
        default=WorkflowStage.INITIAL, description="Current stage in the workflow"
    )
    goal: str = Field(..., description="The initial goal that started the workflow.")
    history: List[WorkflowTransition] = Field(
        default_factory=list, description="Historical record of stage transitions."
    )

    def record_transition(
        self, to_stage: WorkflowStage, reason: Optional[str] = None
    ) -> None:
        """Helper to append a transition to history if the stage changed."""
        if self.current_stage != to_stage:
            self.history.append(
                WorkflowTransition(
                    from_stage=self.current_stage, to_stage=to_stage, reason=reason
                )
            )
            self.current_stage = to_stage


class EpisodicMemory(BaseModel):
    """What happened? Interaction history, event logs."""


class SemanticMemory(BaseModel):
    """What do I know? The knowledge base (RAG), facts about the world and the user."""


class ProceduralMemory(BaseModel):
    """How do I do it? Tool definitions, APIs, user manuals."""


class ResourceMemory(BaseModel):
    """Do I have the resources? System status, API availability, limits."""


class AgentState(BaseModel):
    """Full memory object available to the engine layer."""

    core: ConstitutionalMemory
    working: WorkingMemory
    workflow: WorkflowMemory
    episodic: EpisodicMemory
    semantic: SemanticMemory
    procedural: ProceduralMemory
    resource: ResourceMemory

    def get_hello_world_request(self) -> HelloWorldRequest:
        """Constructs a HelloWorldRequest from the agent state."""
        return HelloWorldRequest(query="Hello, World!")
