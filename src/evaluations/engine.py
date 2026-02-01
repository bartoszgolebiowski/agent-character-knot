"""Core evaluation engine with dynamic model builder and LLM runner.

This module implements the core logic for running quality checks on memory
state using dynamically generated Pydantic models and LLM validation.
"""

from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel, Field, create_model

from src.evaluations.helpers import (
    calculate_score,
    format_check_id_for_field,
    prune_memory_state,
)
from src.evaluations.models import CheckDefinition, CheckResult, EvaluationResult
from src.llm.client import LLMClient
from src.llm.config import LLMConfig


def build_dynamic_evaluation_model(
    checks: list[CheckDefinition],
) -> Type[BaseModel]:
    """Build a Pydantic model with fields for each check result.

    For each check (e.g., LC-001), creates two fields:
    - LC_001_passed: bool (whether the check passed)
    - LC_001_reasoning: str (explanation of the result)

    Args:
        checks: List of CheckDefinition objects

    Returns:
        Dynamically created Pydantic model class
    """
    field_definitions = {}

    for check in checks:
        field_name = format_check_id_for_field(check.check_id)

        # Add passed field (boolean)
        field_definitions[f"{field_name}_passed"] = (
            bool,
            Field(
                description=f"Whether check {check.check_id} ({check.title}) passed",
            ),
        )

        # Add reasoning field (string)
        field_definitions[f"{field_name}_reasoning"] = (
            str,
            Field(
                description=f"Explanation for check {check.check_id} result",
                min_length=10,
            ),
        )

    # Create the dynamic model
    DynamicEvaluationModel = create_model(
        "DynamicEvaluationModel",
        **field_definitions,
    )

    return DynamicEvaluationModel


def build_evaluation_prompt(
    pruned_state: dict[str, Any],
    checks: list[CheckDefinition],
) -> str:
    """Build the LLM prompt for evaluation.

    Args:
        pruned_state: The pruned memory state (without large text fields)
        checks: List of quality checks to perform

    Returns:
        Complete prompt string for the LLM
    """
    system_section = """You are a Quality Assurance Auditor for a Literary AI Memory System.

Your task is to analyze a JSON memory state dump and verify that it meets specific quality criteria.

For each criterion provided, you must:
1. Examine the relevant sections of the JSON state
2. Determine if the criterion is satisfied (true/false)
3. Provide clear reasoning explaining your decision

Be thorough and precise in your analysis. Reference specific data from the JSON when explaining your reasoning."""

    # Format the checks
    checks_section = "# QUALITY CHECKS\n\n"
    for check in checks:
        checks_section += f"## {check.check_id}: {check.title}\n"
        checks_section += f"**Priority**: {check.priority.value}\n\n"
        checks_section += f"**Criterion**: {check.criterion}\n\n"
        checks_section += f"**Verification**: {check.verification}\n\n"

        if check.positive_example:
            checks_section += f"**Positive Example**: {check.positive_example}\n\n"
        if check.negative_example:
            checks_section += f"**Negative Example**: {check.negative_example}\n\n"

        checks_section += "---\n\n"

    # Format the JSON state
    state_json = json.dumps(pruned_state, indent=2)
    state_section = f"# MEMORY STATE TO AUDIT\n\n```json\n{state_json}\n```\n\n"

    # Combine all sections
    prompt = f"{system_section}\n\n{checks_section}{state_section}"
    prompt += "Now evaluate the memory state against ALL criteria above.\n"

    return prompt


def run_evaluation(
    state_path: str,
    checks: list[CheckDefinition],
    llm_client: LLMClient | None = None,
) -> EvaluationResult:
    """Run the complete evaluation process.

    Args:
        state_path: Path to the JSON state dump file
        checks: List of quality checks to perform
        llm_client: Optional LLM client (creates one if not provided)

    Returns:
        EvaluationResult with complete analysis

    Raises:
        FileNotFoundError: If state file doesn't exist
        ValueError: If state file is invalid JSON
    """
    # Load and prune the state
    with open(state_path, encoding="utf-8") as f:
        state_data = json.load(f)

    pruned_state = prune_memory_state(state_data)

    # Build the dynamic model
    EvaluationModel = build_dynamic_evaluation_model(checks)

    # Build the prompt
    prompt = build_evaluation_prompt(pruned_state, checks)

    # Initialize LLM client if not provided
    if llm_client is None:
        # Use higher token limit for evaluation
        config = LLMConfig.from_env()
        # Create new config with higher limits
        eval_config = LLMConfig(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
            temperature=0.1,  # Lower temperature for more consistent evaluation
            max_output_tokens=4000,  # Higher limit for detailed reasoning
        )
        llm_client = LLMClient(config=eval_config)

    # Call the LLM
    llm_response = llm_client.invoke(
        prompt=prompt,
        output_model=EvaluationModel,
    )

    # Parse the response into CheckResult objects
    check_results = []
    response_dict = llm_response.model_dump()

    for check in checks:
        field_name = format_check_id_for_field(check.check_id)
        passed = response_dict[f"{field_name}_passed"]
        reasoning = response_dict[f"{field_name}_reasoning"]

        check_results.append(
            CheckResult(
                check_id=check.check_id,
                passed=passed,
                reasoning=reasoning,
            )
        )

    # Calculate overall score
    score_metrics = calculate_score(
        [r.model_dump() for r in check_results],
        checks,
    )

    # Build final result
    return EvaluationResult(
        total_checks=score_metrics["total_checks"],
        passed_checks=score_metrics["passed_checks"],
        failed_checks=score_metrics["failed_checks"],
        must_have_passed=score_metrics["must_have_passed"],
        must_have_total=score_metrics["must_have_total"],
        overall_status=score_metrics["overall_status"],
        score_percentage=score_metrics["score_percentage"],
        check_results=check_results,
    )
