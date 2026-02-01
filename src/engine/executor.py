from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from pydantic import BaseModel

from src.skills.base import SkillName

from ..llm import LLMClient
from ..skills import skill_registry


@dataclass(frozen=True, slots=True)
class LLMExecutor:
    """Executor responsible for rendering prompts and calling the LLM client."""

    client: LLMClient

    @classmethod
    def from_env(cls) -> "LLMExecutor":
        """Create an executor that uses environment variables for configuration."""

        return cls(client=LLMClient.from_env())

    def execute(self, skill_name: SkillName, context: Dict[str, Any]) -> BaseModel:
        """Render the prompt and call the configured LLM client."""

        definition = skill_registry.get(skill_name)
        prompt = definition.render_prompt(context)
        try:
            output = self.client.invoke(
                prompt=prompt, output_model=definition.output_model
            )
        except Exception as exc:
            raise
        return output
