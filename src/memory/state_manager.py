from __future__ import annotations

from copy import deepcopy
from typing import Callable, Dict, Optional

from pydantic import BaseModel

from src.skills.base import SkillName
from src.skills.models import AnalyzeAndPlanSkillOutput
from src.tools.models import HelloWorldResponse, ToolName

from .models import (
    AgentState,
    ConstitutionalMemory,
    EpisodicMemory,
    ProceduralMemory,
    ResourceMemory,
    SemanticMemory,
    WorkflowMemory,
    WorkingMemory,
)
from src.engine.types import WorkflowStage

SkillHandler = Callable[[AgentState, BaseModel], AgentState]
ToolHandler = Callable[[AgentState, BaseModel], AgentState]


def create_initial_state(
    goal: Optional[str] = None,
    core: Optional[ConstitutionalMemory] = None,
    semantic: Optional[SemanticMemory] = None,
    episodic: Optional[EpisodicMemory] = None,
    workflow: Optional[WorkflowMemory] = None,
    working: Optional[WorkingMemory] = None,
    procedural: Optional[ProceduralMemory] = None,
    resource: Optional[ResourceMemory] = None,
) -> AgentState:
    """Initialize a fully-populated state tree."""
    if goal is None and workflow is None:
        raise ValueError("Either goal or workflow must be provided")

    core = core or ConstitutionalMemory()
    semantic = semantic or SemanticMemory()
    episodic = episodic or EpisodicMemory()
    workflow = workflow or WorkflowMemory(goal=goal)  # type: ignore
    working = working or WorkingMemory()
    procedural = procedural or ProceduralMemory()
    resource = resource or ResourceMemory()

    return AgentState(
        core=core,
        semantic=semantic,
        episodic=episodic,
        workflow=workflow,
        working=working,
        procedural=procedural,
        resource=resource,
    )


def update_state_from_skill(
    state: AgentState, skill: SkillName, output: BaseModel
) -> AgentState:
    """Route a structured skill output to its handler."""

    handler = _SKILL_HANDLERS.get(skill)
    if handler is None:
        raise ValueError(f"No handler registered for skill {skill}")
    return handler(state, output)


def skill_analyze_and_plan_handler(
    state: AgentState, output: AnalyzeAndPlanSkillOutput
) -> AgentState:
    """Handler for analyze and plan skill that updates workflow with analysis and plan."""
    new_state = deepcopy(state)
    # Advance to the recommended stage and record transition
    new_state.workflow.record_transition(
        to_stage=output.next_stage, reason=output.chain_of_thought
    )
    return new_state


_SKILL_HANDLERS: Dict[SkillName, SkillHandler] = {
    SkillName.ANALYZE_AND_PLAN: skill_analyze_and_plan_handler,  # type: ignore
}


def update_state_from_tool(
    state: AgentState, tool: ToolName, output: BaseModel
) -> AgentState:
    """Route a structured tool output to its handler."""

    handler = _TOOL_HANDLERS.get(tool)
    if handler is None:
        raise ValueError(f"No handler registered for tool {tool}")
    return handler(state, output)


def tool_welcome_handler(state: AgentState, output: HelloWorldResponse) -> AgentState:
    """Example tool handler that updates the episodic memory with a welcome message."""
    new_state = deepcopy(state)
    new_state.workflow.record_transition(
        to_stage=WorkflowStage.COORDINATOR, reason="Initial tool execution completed."
    )
    return new_state


_TOOL_HANDLERS: Dict[ToolName, ToolHandler] = {
    ToolName.HELLO_WORLD: tool_welcome_handler,  # type: ignore
}
