"""Public skill registry access."""

from .base import SkillDefinition, SkillRegistry, SkillName
from .definitions import ALL_SKILLS

skill_registry = SkillRegistry()

for definition in ALL_SKILLS:
    skill_registry.register(definition)

__all__ = ["skill_registry", "SkillDefinition", "SkillRegistry", "SkillName"]
