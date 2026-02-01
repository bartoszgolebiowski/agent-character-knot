from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Type

from pydantic import BaseModel

from ..prompting.environment import prompt_environment


class SkillName(str, Enum):
    """LLM skill identifiers used by the coordinator."""

    HELLO_WORLD = "hello_world"
    ANALYZE_AND_PLAN = "analyze_and_plan"

    # FR-04, FR-06, FR-07: Combined chapter analysis skill
    ANALYZE_CHAPTER = "analyze_chapter"

    # FR-05: Importance scoring (batch, runs after all chapters)
    IMPORTANCE_SCORING = "importance_scoring"

    # FR-13: Hierarchical memory consolidation
    CONSOLIDATE_MEMORY = "consolidate_memory"


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Declarative description of a skill."""

    name: SkillName
    template_name: str
    output_model: Type[BaseModel]

    def render_prompt(self, context: Dict[str, Any]) -> str:
        """Render the prompt template with the provided context."""
        template = prompt_environment.get_template(self.template_name)
        return template.render(**context)


class SkillRegistry:
    """Simple container providing lookup for skill definitions."""

    def __init__(self) -> None:
        self._skills: Dict[SkillName, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        self._skills[skill.name] = skill

    def get(self, skill_name: SkillName) -> SkillDefinition:
        if skill_name not in self._skills:
            raise KeyError(f"Skill {skill_name} is not registered")
        return self._skills[skill_name]

    def all(self) -> Dict[SkillName, SkillDefinition]:
        return dict(self._skills)
