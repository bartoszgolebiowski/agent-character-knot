"""Helper utilities for evaluation framework.

This module provides utility functions for preparing and processing
memory state data for evaluation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def prune_memory_state(state_data: dict[str, Any]) -> dict[str, Any]:
    """Remove large/irrelevant fields from state to save tokens.

    This function removes:
    - working.current_chapter_text (large text content)
    - working.chapter_map (redundant mapping data)

    While keeping:
    - semantic (character profiles, relationships)
    - episodic (chapter summaries, events)
    - Other metadata fields

    Args:
        state_data: Raw state dictionary loaded from JSON

    Returns:
        Pruned copy of state data with large fields removed
    """
    # Create a deep copy to avoid mutating original
    pruned = deepcopy(state_data)

    # Remove large text content from working memory
    if "working" in pruned:
        if "current_chapter_text" in pruned["working"]:
            del pruned["working"]["current_chapter_text"]
        if "chapter_map" in pruned["working"]:
            del pruned["working"]["chapter_map"]

    return pruned


def format_check_id_for_field(check_id: str) -> str:
    """Convert check ID to valid Python field name.

    Converts 'LC-001' to 'LC_001' for use in Pydantic models.

    Args:
        check_id: Check ID in format 'XX-NNN'

    Returns:
        Field-safe version with underscores
    """
    return check_id.replace("-", "_")


def calculate_score(
    check_results: list[dict[str, Any]],
    check_definitions: list[Any],
) -> dict[str, Any]:
    """Calculate overall evaluation score from check results.

    Args:
        check_results: List of check results from LLM
        check_definitions: List of CheckDefinition objects

    Returns:
        Dictionary with score metrics:
        - total_checks: Total number of checks
        - passed_checks: Number that passed
        - failed_checks: Number that failed
        - must_have_passed: MUST-HAVE checks that passed
        - must_have_total: Total MUST-HAVE checks
        - score_percentage: Overall percentage score
        - overall_status: 'PASS' if all MUST-HAVE pass, else 'FAIL'
    """
    from src.evaluations.models import CheckPriority

    total = len(check_results)
    passed = sum(1 for r in check_results if r.get("passed", False))
    failed = total - passed

    # Create lookup map for priorities
    priority_map = {check.check_id: check.priority for check in check_definitions}

    # Count MUST-HAVE results
    must_have_total = sum(
        1
        for check_id, priority in priority_map.items()
        if priority == CheckPriority.MUST_HAVE
    )
    must_have_passed = sum(
        1
        for r in check_results
        if r.get("passed", False)
        and priority_map.get(r["check_id"]) == CheckPriority.MUST_HAVE
    )

    # Calculate percentage
    score_percentage = (passed / total * 100) if total > 0 else 0.0

    # Overall status: PASS only if all MUST-HAVE checks pass
    overall_status = "PASS" if must_have_passed == must_have_total else "FAIL"

    return {
        "total_checks": total,
        "passed_checks": passed,
        "failed_checks": failed,
        "must_have_passed": must_have_passed,
        "must_have_total": must_have_total,
        "score_percentage": round(score_percentage, 2),
        "overall_status": overall_status,
    }
