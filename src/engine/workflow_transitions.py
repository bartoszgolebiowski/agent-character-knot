from __future__ import annotations

"""Workflow state machine transitions for StoryGraph Agent.

This module defines the TRANSITIONS table which maps each WorkflowStage
to its corresponding action. The Coordinator uses this table to make
deterministic decisions about what to do next.

Flow:
    INITIAL -> SEGMENTATION -> LOAD_CHAPTER -> ANALYZE_CHAPTER
    -> CHECK_COMPLETION -> (loop back to LOAD_CHAPTER or proceed)
    -> IMPORTANCE_SCORING -> GENERATE_REPORT -> COMPLETED
"""

from typing import Dict, Optional, Tuple, Union

from ..skills.base import SkillName
from ..tools.models import ToolName
from .types import ActionType, WorkflowStage


# Type for transition table entries
TransitionEntry = Tuple[ActionType, Union[SkillName, ToolName, None], str]


# =============================================================================
# Main Transition Table
# =============================================================================

TRANSITIONS: Dict[WorkflowStage, TransitionEntry] = {
    # Phase 0: Initialization
    WorkflowStage.INITIAL: (
        ActionType.TOOL,
        ToolName.CHAPTER_SEGMENTATION,
        "Detecting chapter boundaries in the source text",
    ),
    # Phase 1: Data Ingestion - Segmentation done, load first chapter
    WorkflowStage.SEGMENTATION: (
        ActionType.TOOL,
        ToolName.CHAPTER_SEGMENTATION,
        "Segmenting the book into chapters",
    ),
    # Phase 2: Load current chapter
    WorkflowStage.LOAD_CHAPTER: (
        ActionType.TOOL,
        ToolName.CHAPTER_EXTRACTION,
        "Extracting current chapter text",
    ),
    # Phase 3: Analyze chapter (entity resolution, relationships, events)
    WorkflowStage.ANALYZE_CHAPTER: (
        ActionType.LLM_SKILL,
        SkillName.ANALYZE_CHAPTER,
        "Analyzing chapter for characters, relationships, and events",
    ),
    # Phase 4: Check if more chapters to process
    # NOTE: CHECK_COMPLETION is handled specially in the Coordinator
    # to implement the chapter iteration loop
    WorkflowStage.CHECK_COMPLETION: (
        ActionType.NOOP,
        None,
        "Checking if more chapters remain",
    ),
    # Phase 5: Score character importance (batch, after all chapters)
    WorkflowStage.IMPORTANCE_SCORING: (
        ActionType.LLM_SKILL,
        SkillName.IMPORTANCE_SCORING,
        "Computing importance scores for all characters",
    ),
    # Phase 6: Generate HTML report
    WorkflowStage.GENERATE_REPORT: (
        ActionType.TOOL,
        ToolName.HTML_REPORT_GENERATION,
        "Generating multi-page HTML report",
    ),
    # Terminal states
    WorkflowStage.COMPLETED: (
        ActionType.COMPLETE,
        None,
        "Workflow completed successfully",
    ),
    WorkflowStage.ERROR: (
        ActionType.COMPLETE,
        None,
        "Workflow stopped due to error",
    ),
    # Legacy: COORDINATOR stage for routing decisions
    WorkflowStage.COORDINATOR: (
        ActionType.LLM_SKILL,
        SkillName.ANALYZE_AND_PLAN,
        "Coordinating next actions based on current state",
    ),
}
