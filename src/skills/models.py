from __future__ import annotations


from pydantic import BaseModel, Field

from src.engine.types import WorkflowStage


class AnalyzeAndPlanSkillOutput(BaseModel):
    """Structured fields returned by the analyze and plan skill."""

    chain_of_thought: str = Field(
        default="",
        description="Detailed reasoning about the user's query and the context.",
    )
    next_stage: WorkflowStage = Field(
        default=WorkflowStage.COORDINATOR,
        description="Recommended next workflow stage.",
    )
