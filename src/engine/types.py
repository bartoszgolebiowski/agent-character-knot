from __future__ import annotations

from enum import Enum


class ActionType(str, Enum):
    """Types of actions that the coordinator can request."""

    LLM_SKILL = "llm_skill"
    TOOL = "tool"
    COMPLETE = "complete"
    NOOP = "noop"


class WorkflowStage(str, Enum):
    """Defines the stages of the agent workflow (FR-03: Sequential Processing)."""

    # Initialization Stage
    INITIAL = "INITIAL"

    # Phase 1: Data Ingestion
    SEGMENTATION = "SEGMENTATION"  # Detect chapter boundaries
    LOAD_CHAPTER = "LOAD_CHAPTER"  # Extract current chapter text

    # Phase 2: Chapter Analysis (repeated for each chapter)
    ANALYZE_CHAPTER = "ANALYZE_CHAPTER"  # Combined entity/relationship/event extraction

    # Phase 3: Check Completion
    CHECK_COMPLETION = (
        "CHECK_COMPLETION"  # Decide if more chapters or proceed to scoring
    )

    # Phase 3b: Hierarchical Memory Consolidation
    CONSOLIDATE_MEMORY = "CONSOLIDATE_MEMORY"

    # Phase 4: Final Processing
    IMPORTANCE_SCORING = "IMPORTANCE_SCORING"  # Score all characters
    GENERATE_REPORT = "GENERATE_REPORT"  # Create HTML report

    # Terminal Stages
    COORDINATOR = "COORDINATOR"  # Legacy: used for routing decisions
    COMPLETED = "COMPLETED"  # Workflow finished successfully
    ERROR = "ERROR"  # Workflow encountered an error
