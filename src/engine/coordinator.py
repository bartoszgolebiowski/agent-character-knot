from __future__ import annotations

from .decision import CoordinatorDecision
from .types import ActionType, WorkflowStage
from .workflow_transitions import TRANSITIONS
from ..memory.models import AgentState
from ..skills.base import SkillName
from ..tools.models import ToolName


class AgentActionCoordinator:
    """Deterministic state machine that decides the next action.

    The coordinator implements the core routing logic for the StoryGraph agent.
    It uses a table-driven approach (TRANSITIONS map) for most stages, with
    special handling for the CHECK_COMPLETION stage to implement chapter iteration.
    """

    def next_action(self, state: AgentState) -> CoordinatorDecision:
        """Decide the next action based on the current agent state.

        Args:
            state: Current AgentState containing workflow stage and context

        Returns:
            CoordinatorDecision indicating what action to take next
        """
        current_stage = state.workflow.current_stage

        # Special case: CHECK_COMPLETION implements chapter iteration (FR-03)
        if current_stage == WorkflowStage.CHECK_COMPLETION:
            return self._handle_chapter_iteration(state)

        # Default: Lookup from transitions table
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

    def _handle_chapter_iteration(self, state: AgentState) -> CoordinatorDecision:
        """Handle the chapter iteration logic (FR-03: Sequential Processing).

        This method implements the core loop:
        - If more chapters remain: return to LOAD_CHAPTER
        - If all chapters done: proceed to IMPORTANCE_SCORING

        The actual stage advancement happens in the state handlers, so this
        method modifies the state in-place to prepare for the next iteration.
        """
        current_idx = state.working.current_chapter_index
        total = state.working.total_chapters

        if current_idx < total - 1:
            # More chapters to process -> increment index and load next
            # Note: The state update happens via the handler, but we need
            # to return the right decision
            return CoordinatorDecision.tool(
                tool=ToolName.CHAPTER_EXTRACTION,
                reason=f"Loading chapter {current_idx + 2} of {total}",
            )
        else:
            # All chapters processed -> proceed to importance scoring
            return CoordinatorDecision.llm(
                skill=SkillName.IMPORTANCE_SCORING,
                reason="All chapters processed, computing character importance scores",
            )
