from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

from src.engine.decision import ActionType, CoordinatorDecision
from src.engine.types import WorkflowStage
from src.memory.models import AgentState
from src.memory.state_manager import advance_to_next_chapter, update_state_from_tool
from src.skills.base import SkillName
from src.tools.chapter_extraction import ChapterExtractionTool
from src.tools.chapter_segmentation import ChapterSegmentationTool
from src.tools.hello_world import HelloWorldClient
from src.tools.html_report_generator import HTMLReportGeneratorTool
from src.tools.models import (
    ChapterExtractionRequest,
    ChapterSegmentationRequest,
    HTMLReportRequest,
    ToolName,
)

from src.engine import LLMExecutor, AgentActionCoordinator
from src.llm import LLMCallError
from src.logger import get_agent_logger
from src.memory import (
    create_initial_state,
    update_state_from_skill,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Runtime configuration for the agent."""

    iteration_step_limit: int = 500  # Increased for large books
    output_directory: str = "output/report"
    report_title: str = "StoryGraph Character Analysis"


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Return value from a full agent run."""

    state: AgentState
    steps_executed: int
    report_path: Optional[str] = None

    def summary(self) -> str:
        """Generate a human-readable summary of the agent run."""
        char_count = len(self.state.semantic.characters)
        rel_pairs: set[tuple[str, str]] = set()
        for char_id, rels in self.state.semantic.relationships.items():
            for other_id in rels.keys():
                if char_id < other_id:
                    rel_pairs.add((char_id, other_id))
        rel_count = len(rel_pairs)
        event_count = len(self.state.semantic.event_chronicle)
        chapters = self.state.working.total_chapters

        return (
            f"StoryGraph Analysis Complete\n"
            f"----------------------------\n"
            f"Chapters Processed: {chapters}\n"
            f"Characters Found: {char_count}\n"
            f"Relationships Mapped: {rel_count}\n"
            f"Significant Events: {event_count}\n"
            f"Steps Executed: {self.steps_executed}\n"
            f"Report Location: {self.report_path or 'Not generated'}"
        )


class Agent:
    """High-level entry point for the StoryGraph AI Agent.

    This agent orchestrates the analysis of literary works by:
    1. Segmenting books into chapters
    2. Extracting characters, relationships, and events
    3. Building a knowledge graph with evidence-based attribution
    4. Generating an interactive HTML report
    """

    def __init__(
        self,
        *,
        llm_executor: LLMExecutor,
        hello_world_client: HelloWorldClient,
        segmentation_tool: ChapterSegmentationTool,
        extraction_tool: ChapterExtractionTool,
        report_generator: HTMLReportGeneratorTool,
        config: Optional[AgentConfig] = None,
        coordinator: Optional[AgentActionCoordinator] = None,
    ) -> None:
        self._llm_executor = llm_executor
        self._hello_world_client = hello_world_client
        self._segmentation_tool = segmentation_tool
        self._extraction_tool = extraction_tool
        self._report_generator = report_generator
        self._config = config or AgentConfig()
        self._coordinator = coordinator or AgentActionCoordinator()
        self._logger = get_agent_logger()

    @classmethod
    def from_env(
        cls,
        *,
        agent_config: Optional[AgentConfig] = None,
    ) -> "Agent":
        """Create an agent wired to environment-configured dependencies."""
        llm_executor = LLMExecutor.from_env()
        hello_world_client = HelloWorldClient()
        segmentation_tool = ChapterSegmentationTool()
        extraction_tool = ChapterExtractionTool()
        report_generator = HTMLReportGeneratorTool()

        return cls(
            llm_executor=llm_executor,
            hello_world_client=hello_world_client,
            segmentation_tool=segmentation_tool,
            extraction_tool=extraction_tool,
            report_generator=report_generator,
            config=agent_config,
        )

    def run(
        self,
        goal: str,
        source_file_path: Optional[str] = None,
        book_title: str = "Unknown Book",
    ) -> AgentResult:
        """Execute the StoryGraph analysis workflow.

        Args:
            goal: Description of what to analyze (e.g., "Analyze War and Peace")
            source_file_path: Path to the text file to analyze
            book_title: Title of the book for the report

        Returns:
            AgentResult containing final state and execution stats
        """
        # Validate source file if provided
        if source_file_path:
            if not Path(source_file_path).exists():
                raise FileNotFoundError(f"Source file not found: {source_file_path}")

        state = create_initial_state(
            goal=goal,
            source_file_path=source_file_path or "",
            book_title=book_title,
        )

        steps_executed = 0
        report_path: Optional[str] = None

        self._logger.info(f"Starting StoryGraph analysis: {goal}")
        self._logger.info(f"Source: {source_file_path or 'Not specified'}")

        for step in range(self._config.iteration_step_limit):
            steps_executed = step + 1
            decision = self._coordinator.next_action(state)
            self._log_decision(decision, state)

            # Log progress for chapter processing
            if state.workflow.current_stage == WorkflowStage.ANALYZE_CHAPTER:
                current = state.working.current_chapter_index + 1
                total = state.working.total_chapters
                self._logger.info(f"Processing Chapter {current}/{total}")

            if decision.action_type == ActionType.COMPLETE:
                self._logger.info("Workflow completed successfully")
                break

            if decision.action_type == ActionType.NOOP:
                self._logger.warning(f"NOOP: {decision.reason}")
                break

            if decision.action_type == ActionType.LLM_SKILL and decision.skill:
                context = self._build_prompt_context(state)
                self._log_llm_request(decision.skill, context)
                output = self._llm_call(decision.skill, context)
                self._log_llm_response(decision.skill, output)
                state = update_state_from_skill(state, decision.skill, output)
                continue

            if decision.action_type == ActionType.TOOL and decision.tool_type:
                self._logger.info(f"Executing tool: {decision.tool_type.value}")

                if (
                    state.workflow.current_stage == WorkflowStage.CHECK_COMPLETION
                    and decision.tool_type == ToolName.CHAPTER_EXTRACTION
                ):
                    state = advance_to_next_chapter(state)

                output = self._execute_tool(state, decision.tool_type)
                self._logger.info(
                    f"Tool execution complete: {decision.tool_type.value}"
                )
                state = update_state_from_tool(state, decision.tool_type, output)

                # Capture report path if report was generated
                if decision.tool_type == ToolName.HTML_REPORT_GENERATION:
                    from src.tools.models import HTMLReportResult

                    if isinstance(output, HTMLReportResult):
                        report_path = output.index_file

                continue

            raise RuntimeError(f"Unhandled coordinator decision: {decision}")
        else:
            # Only executed if the for-loop does not break
            message = (
                f"Reached step limit ({self._config.iteration_step_limit}) "
                "before completion. Consider increasing max_steps."
            )
            logger.warning(message)
            self._logger.warning(message)

        return AgentResult(
            state=state,
            steps_executed=steps_executed,
            report_path=report_path,
        )

    def _build_prompt_context(self, state: AgentState) -> Dict[str, object]:
        """Build the context dictionary for prompt rendering."""
        return {
            "state": state,
            "core": state.core,
            "semantic": state.semantic,
            "episodic": state.episodic,
            "workflow": state.workflow,
            "working": state.working,
            "procedural": state.procedural,
            "resource": state.resource,
            # Convenience accessors for templates
            "current_chapter_text": state.working.current_chapter_text,
            "current_chapter_title": state.working.current_chapter_title,
            "current_chapter_index": state.working.current_chapter_index,
            "characters": state.semantic.characters,
            "relationships": state.semantic.relationships,
            "events": state.semantic.event_chronicle,
        }

    def _log_decision(self, decision: CoordinatorDecision, state: AgentState) -> None:
        self._logger.info(
            "Coordinator decision: "
            f"stage={state.workflow.current_stage.value}, "
            f"action={decision.action_type.value}, "
            f"skill={decision.skill.value if decision.skill else 'n/a'}, "
            f"tool={decision.tool_type.value if decision.tool_type else 'n/a'}, "
            f"reason={decision.reason}",
        )

    def _context_summary(self, context: Dict[str, object]) -> Dict[str, object]:
        text = context.get("current_chapter_text") or ""
        return {
            "stage": context["workflow"].current_stage.value,
            "chapter_index": context["working"].current_chapter_index,
            "chapter_title": context["working"].current_chapter_title,
            "chapter_text_length": len(text),
            "characters_tracked": len(context.get("characters", [])),
        }

    def _log_llm_request(
        self, skill_name: SkillName, context: Dict[str, object]
    ) -> None:
        summary = self._context_summary(context)
        self._logger.info(
            f"LLM request {skill_name.value}: {json.dumps(summary, ensure_ascii=False)}"
        )

    def _log_llm_response(self, skill_name: SkillName, output: BaseModel) -> None:
        self._logger.info(
            f"LLM response {skill_name.value}: {self._format_payload(output)}"
        )

    def _log_tool_request(self, tool_type: ToolName, request: object) -> None:
        self._logger.info(
            f"Tool request {tool_type.value}: {self._format_payload(request)}"
        )

    def _log_tool_response(self, tool_type: ToolName, response: BaseModel) -> None:
        self._logger.info(
            f"Tool response {tool_type.value}: {self._format_payload(response)}"
        )

    def _format_payload(self, payload: object) -> str:
        if isinstance(payload, BaseModel):
            data = payload.model_dump(exclude_none=True)
        else:
            data = payload
        try:
            return json.dumps(data, default=str, ensure_ascii=False)
        except TypeError:
            return str(data)

    def _llm_call(self, skill_name: SkillName, context: Dict[str, object]) -> BaseModel:
        """Execute an LLM skill and return the structured output."""
        try:
            return self._llm_executor.execute(skill_name, context)
        except LLMCallError as exc:
            raise RuntimeError(
                f"LLM call failed for {skill_name.value}: {exc}"
            ) from exc

    def _execute_tool(self, state: AgentState, tool_type: ToolName) -> BaseModel:
        """Execute a tool and return its result."""
        if tool_type == ToolName.HELLO_WORLD:
            request_payload = state.get_hello_world_request()
            self._log_tool_request(tool_type, request_payload)
            response = self._hello_world_client.call(request_payload)
            self._log_tool_response(tool_type, response)
            return response

        elif tool_type == ToolName.CHAPTER_SEGMENTATION:
            request = ChapterSegmentationRequest(
                file_path=state.working.source_file_path,
            )
            self._log_tool_request(tool_type, request)
            response = self._segmentation_tool.segment(request)
            self._log_tool_response(tool_type, response)
            return response

        elif tool_type == ToolName.CHAPTER_EXTRACTION:
            # Convert ChapterMetadata to ChapterSegmentationMetadata for the request
            from src.tools.models import ChapterSegmentationMetadata

            chapter_map = [
                ChapterSegmentationMetadata(
                    index=cm.index,
                    title=cm.title,
                    book_index=cm.book_index,
                    book_title=cm.book_title,
                    chapter_number=cm.chapter_number,
                    start_line=cm.start_line,
                    end_line=cm.end_line,
                    line_count=cm.line_count,
                )
                for cm in state.working.chapter_map
            ]

            request = ChapterExtractionRequest(
                file_path=state.working.source_file_path,
                chapter_index=state.working.current_chapter_index,
                chapter_map=chapter_map,
            )
            self._log_tool_request(tool_type, request)
            response = self._extraction_tool.extract(request)
            self._log_tool_response(tool_type, response)
            return response

        elif tool_type == ToolName.HTML_REPORT_GENERATION:
            request = HTMLReportRequest(
                output_directory=self._config.output_directory,
                report_title=self._config.report_title,
                book_title=state.working.book_title,
            )
            self._log_tool_request(tool_type, request)
            response = self._report_generator.generate(request, state)
            self._log_tool_response(tool_type, response)
            return response

        else:
            raise RuntimeError(f"Unknown tool type requested: {tool_type}")
