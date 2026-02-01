"""Data models for evaluation framework.

This module defines the core data structures for loading, validating,
and reporting on memory state quality.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class CheckPriority(str, Enum):
    """Priority levels for quality checks."""

    MUST_HAVE = "MUST-HAVE"
    SHOULD_HAVE = "SHOULD-HAVE"
    NICE_TO_HAVE = "NICE-TO-HAVE"


class CheckDefinition(BaseModel):
    """Definition of a single quality check parsed from Markdown.

    Attributes:
        check_id: Unique identifier (e.g., 'LC-001')
        priority: Priority level (MUST-HAVE, SHOULD-HAVE, NICE-TO-HAVE)
        title: Human-readable name for the check
        criterion: What is being verified
        verification: How to verify it
        positive_example: Optional example of passing case
        negative_example: Optional example of failing case
    """

    check_id: str = Field(
        description="Unique identifier for this check (e.g., 'LC-001')",
        pattern=r"^[A-Z]{2,4}-\d{3}$",
    )
    priority: CheckPriority = Field(
        description="Priority level for this check",
    )
    title: str = Field(
        description="Human-readable name for the check",
        min_length=3,
    )
    criterion: str = Field(
        description="What is being verified in this check",
        min_length=10,
    )
    verification: str = Field(
        description="How to verify this criterion",
        min_length=10,
    )
    positive_example: str | None = Field(
        default=None,
        description="Example of passing case",
    )
    negative_example: str | None = Field(
        default=None,
        description="Example of failing case",
    )


class CheckResult(BaseModel):
    """Result of a single quality check.

    Attributes:
        check_id: Reference to the CheckDefinition
        passed: Whether the check passed
        reasoning: Explanation of the result
    """

    check_id: str = Field(
        description="Reference to the CheckDefinition ID",
    )
    passed: bool = Field(
        description="Whether the check passed",
    )
    reasoning: str = Field(
        description="Explanation of why this check passed or failed",
        min_length=10,
    )


class EvaluationResult(BaseModel):
    """Complete evaluation result for a memory state.

    Attributes:
        total_checks: Total number of checks performed
        passed_checks: Number of checks that passed
        failed_checks: Number of checks that failed
        must_have_passed: Number of MUST-HAVE checks that passed
        must_have_total: Total number of MUST-HAVE checks
        overall_status: Overall evaluation status
        check_results: Individual check results
        score_percentage: Overall score as percentage
    """

    total_checks: int = Field(
        ge=0,
        description="Total number of checks performed",
    )
    passed_checks: int = Field(
        ge=0,
        description="Number of checks that passed",
    )
    failed_checks: int = Field(
        ge=0,
        description="Number of checks that failed",
    )
    must_have_passed: int = Field(
        ge=0,
        description="Number of MUST-HAVE checks that passed",
    )
    must_have_total: int = Field(
        ge=0,
        description="Total number of MUST-HAVE checks",
    )
    overall_status: Literal["PASS", "FAIL"] = Field(
        description="Overall evaluation status (PASS if all MUST-HAVE pass)",
    )
    check_results: list[CheckResult] = Field(
        description="Individual check results",
    )
    score_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall score as percentage",
    )
