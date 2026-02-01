from __future__ import annotations

from typing import Dict, Tuple, Union

from .types import ActionType, WorkflowStage
from ..skills.base import SkillName
from ..tools.models import ToolName


TRANSITIONS: Dict[WorkflowStage, Tuple[ActionType, Union[SkillName, ToolName], str]] = {
    WorkflowStage.INITIAL: (
        ActionType.TOOL,
        ToolName.HELLO_WORLD,
        "Analyzing the user query and planning next steps",
    ),
    WorkflowStage.COORDINATOR: (
        ActionType.LLM_SKILL,
        SkillName.ANALYZE_AND_PLAN,
        "Coordinating the next actions based on the current state",
    ),
    WorkflowStage.COMPLETED: (
        ActionType.COMPLETE,
        SkillName.HELLO_WORLD,
        "Workflow completed successfully",
    ),
}
