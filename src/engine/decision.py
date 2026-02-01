from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.logger import get_agent_logger
from src.skills.base import SkillName
from src.tools.models import ToolName
from .types import ActionType

_logger = get_agent_logger()


@dataclass(frozen=True, slots=True)
class CoordinatorDecision:
    """Structured instruction emitted by the coordinator."""

    action_type: ActionType
    skill: Optional[SkillName] = None
    tool_type: Optional[ToolName] = None
    task_id: Optional[str] = None
    reason: str = ""

    @staticmethod
    def llm(skill: SkillName, reason: str) -> "CoordinatorDecision":
        _logger.debug(f"Creating LLM decision: skill={skill.value}, reason={reason}")
        return CoordinatorDecision(
            action_type=ActionType.LLM_SKILL,
            skill=skill,
            reason=reason,
        )

    @staticmethod
    def tool(tool: ToolName, reason: str) -> "CoordinatorDecision":
        _logger.debug(f"Creating tool decision: tool={tool.value}, reason={reason}")
        return CoordinatorDecision(
            action_type=ActionType.TOOL,
            tool_type=tool,
            reason=reason,
        )

    @staticmethod
    def complete(reason: str) -> "CoordinatorDecision":
        _logger.debug(f"Creating complete decision: reason={reason}")
        return CoordinatorDecision(action_type=ActionType.COMPLETE, reason=reason)

    @staticmethod
    def noop(reason: str) -> "CoordinatorDecision":
        _logger.debug(f"Creating noop decision: reason={reason}")
        return CoordinatorDecision(action_type=ActionType.NOOP, reason=reason)
