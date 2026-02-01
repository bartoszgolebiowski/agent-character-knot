from __future__ import annotations

"""Skill definitions used by the StoryGraph workflow."""

from .base import SkillDefinition, SkillName
from .models import (
    AnalyzeAndPlanSkillOutput,
    ChapterAnalysisOutput,
    ConsolidatedMemoryOutput,
    ImportanceScoringOutput,
)


# =============================================================================
# Legacy/Utility Skills
# =============================================================================

ANALYZE_AND_PLAN_SKILL = SkillDefinition(
    name=SkillName.ANALYZE_AND_PLAN,
    template_name="skills/analyze_and_plan.j2",
    output_model=AnalyzeAndPlanSkillOutput,
)


# =============================================================================
# Core Analysis Skills (FR-04, FR-06, FR-07)
# =============================================================================

ANALYZE_CHAPTER_SKILL = SkillDefinition(
    name=SkillName.ANALYZE_CHAPTER,
    template_name="skills/analyze_chapter.j2",
    output_model=ChapterAnalysisOutput,
)


# =============================================================================
# Batch Processing Skills (FR-05)
# =============================================================================

IMPORTANCE_SCORING_SKILL = SkillDefinition(
    name=SkillName.IMPORTANCE_SCORING,
    template_name="skills/importance_scoring.j2",
    output_model=ImportanceScoringOutput,
)


# =============================================================================
# Memory Consolidation Skills (FR-13)
# =============================================================================

CONSOLIDATE_MEMORY_SKILL = SkillDefinition(
    name=SkillName.CONSOLIDATE_MEMORY,
    template_name="skills/consolidate_memory.j2",
    output_model=ConsolidatedMemoryOutput,
)


# =============================================================================
# Skill Registry
# =============================================================================

ALL_SKILLS = [
    ANALYZE_AND_PLAN_SKILL,
    ANALYZE_CHAPTER_SKILL,
    IMPORTANCE_SCORING_SKILL,
    CONSOLIDATE_MEMORY_SKILL,
]
