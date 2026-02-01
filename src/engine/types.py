from __future__ import annotations

from enum import Enum


class ActionType(str, Enum):
    """Types of actions that the coordinator can request."""

    LLM_SKILL = "llm_skill"
    TOOL = "tool"
    COMPLETE = "complete"
    NOOP = "noop"


class WorkflowStage(str, Enum):
    """Defines the stages of the agent workflow."""

    INITIAL = "INITIAL"
    COORDINATOR = "COORDINATOR"
    COMPLETED = "COMPLETED"
    # Add other stages as needed
