from __future__ import annotations

from .decision import CoordinatorDecision
from .workflow_transitions import TRANSITIONS
from .types import ActionType
from ..memory.models import AgentState


class AgentActionCoordinator:
    """Deterministic state machine that decides the next action."""

    def next_action(self, state: AgentState) -> CoordinatorDecision:
        """Decide the next action based on the current agent state."""
        current_stage = state.workflow.current_stage

        if current_stage in TRANSITIONS:
            action_type, name, reason = TRANSITIONS[current_stage]

            if action_type == ActionType.LLM_SKILL:
                return CoordinatorDecision.llm(skill=name, reason=reason)  # type: ignore
            elif action_type == ActionType.TOOL:
                return CoordinatorDecision.tool(tool=name, reason=reason)  # type: ignore
            elif action_type == ActionType.COMPLETE:
                return CoordinatorDecision.complete(reason=reason)
            else:
                return CoordinatorDecision.noop(
                    reason=f"Unsupported action type: {action_type}"
                )
        else:
            return CoordinatorDecision.noop(
                reason=f"No transition defined for stage: {current_stage}"
            )
