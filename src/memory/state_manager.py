from __future__ import annotations

from copy import deepcopy
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel

from src.engine.types import WorkflowStage
from src.skills.base import SkillName
from src.skills.models import (
    AnalyzeAndPlanSkillOutput,
    ChapterAnalysisOutput,
    ImportanceScoringOutput,
)
from src.tools.models import (
    ChapterExtractionResult,
    ChapterSegmentationResult,
    HelloWorldResponse,
    HTMLReportResult,
    ToolName,
)

from .models import (
    AgentState,
    BookMetadata,
    CausalLink,
    CharacterProfile,
    ChapterMetadata,
    ChapterSummary,
    ConstitutionalMemory,
    EpisodicMemory,
    ProceduralMemory,
    RelationshipEvidence,
    RelationshipHistory,
    RelationshipInteraction,
    ResourceMemory,
    SemanticMemory,
    SignificantEvent,
    WorkflowMemory,
    WorkingMemory,
)

# Type aliases for handlers
SkillHandler = Callable[[AgentState, BaseModel], AgentState]
ToolHandler = Callable[[AgentState, BaseModel], AgentState]


# =============================================================================
# State Factory
# =============================================================================


def create_initial_state(
    goal: Optional[str] = None,
    source_file_path: str = "",
    book_title: str = "Unknown Book",
    core: Optional[ConstitutionalMemory] = None,
    semantic: Optional[SemanticMemory] = None,
    episodic: Optional[EpisodicMemory] = None,
    workflow: Optional[WorkflowMemory] = None,
    working: Optional[WorkingMemory] = None,
    procedural: Optional[ProceduralMemory] = None,
    resource: Optional[ResourceMemory] = None,
) -> AgentState:
    """Initialize a fully-populated state tree for StoryGraph analysis."""
    if goal is None and workflow is None:
        raise ValueError("Either goal or workflow must be provided")

    core = core or ConstitutionalMemory()
    semantic = semantic or SemanticMemory()
    episodic = episodic or EpisodicMemory()
    workflow = workflow or WorkflowMemory(goal=goal)  # type: ignore
    working = working or WorkingMemory(
        source_file_path=source_file_path,
        book_title=book_title,
    )
    procedural = procedural or ProceduralMemory(
        available_tools=[
            "chapter_segmentation",
            "chapter_extraction",
            "html_report_generation",
        ]
    )
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


# =============================================================================
# Skill Handlers
# =============================================================================


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
    """Handler for analyze and plan skill that updates workflow with analysis."""
    new_state = deepcopy(state)
    new_state.workflow.record_transition(
        to_stage=output.next_stage, reason=output.chain_of_thought
    )
    return new_state


def skill_analyze_chapter_handler(
    state: AgentState, output: ChapterAnalysisOutput
) -> AgentState:
    """Handler for chapter analysis that updates semantic memory (FR-04, FR-06, FR-07, FR-08).

    This handler:
    1. Processes entity resolution (new characters, alias mappings)
    2. Processes relationship extraction (new interactions)
    3. Processes event extraction (significant events, causal links)
    4. Updates episodic memory with chapter summary
    5. Advances workflow to CHECK_COMPLETION stage
    """
    new_state = deepcopy(state)

    chapter_index = new_state.working.current_chapter_index
    chapter_title = new_state.working.current_chapter_title

    # -------------------------------------------------------------------------
    # 1. Process Entity Resolution (FR-04)
    # -------------------------------------------------------------------------
    entity_data = output.entity_resolution

    # Add new characters to registry
    for new_char in entity_data.new_characters:
        char_id = str(uuid4())
        profile = CharacterProfile(
            id=char_id,
            canonical_name=new_char.suggested_canonical_name,
            aliases=new_char.aliases,
            first_appearance_chapter=chapter_index,
            description=new_char.description,
        )
        new_state.semantic.characters[char_id] = profile

        # Add to alias index
        new_state.semantic.alias_index[new_char.suggested_canonical_name.lower()] = (
            char_id
        )
        for alias in new_char.aliases:
            new_state.semantic.alias_index[alias.lower()] = char_id

    # Process alias mappings for existing characters
    for mapping in entity_data.alias_mappings:
        if (
            mapping.canonical_id
            and mapping.canonical_id in new_state.semantic.characters
        ):
            char_profile = new_state.semantic.characters[mapping.canonical_id]
            if mapping.alias not in char_profile.aliases:
                char_profile.aliases.append(mapping.alias)
            # Update alias index
            new_state.semantic.alias_index[mapping.alias.lower()] = mapping.canonical_id

    # -------------------------------------------------------------------------
    # 2. Process Relationship Extraction (FR-06)
    # -------------------------------------------------------------------------
    rel_data = output.relationship_extraction
    relationships_added = 0

    for interaction_out in rel_data.interactions:
        # Resolve character names to IDs
        char_a_id = _resolve_character_id(new_state, interaction_out.character_a_name)
        char_b_id = _resolve_character_id(new_state, interaction_out.character_b_name)

        if not char_a_id or not char_b_id:
            continue  # Skip if we can't resolve both characters

        # Get or create relationship history (bidirectional)
        if char_a_id not in new_state.semantic.relationships:
            new_state.semantic.relationships[char_a_id] = {}
        if char_b_id not in new_state.semantic.relationships[char_a_id]:
            new_state.semantic.relationships[char_a_id][char_b_id] = (
                RelationshipHistory(
                    character_a_id=char_a_id,
                    character_b_id=char_b_id,
                )
            )

        if char_b_id not in new_state.semantic.relationships:
            new_state.semantic.relationships[char_b_id] = {}
        if char_a_id not in new_state.semantic.relationships[char_b_id]:
            new_state.semantic.relationships[char_b_id][char_a_id] = (
                RelationshipHistory(
                    character_a_id=char_b_id,
                    character_b_id=char_a_id,
                )
            )

        referenced_event_id: Optional[str] = None
        if interaction_out.references_past_event:
            referenced_event = _find_event_by_description(
                new_state.semantic.event_chronicle,
                interaction_out.references_past_event,
            )
            if referenced_event:
                referenced_event_id = referenced_event.event_id

        # Create interaction record
        interaction = RelationshipInteraction(
            character_a_id=char_a_id,
            character_b_id=char_b_id,
            relation_type=interaction_out.relation_type,
            reasoning=interaction_out.reasoning,
            context=interaction_out.context,
            evidence=RelationshipEvidence(
                quote=interaction_out.evidence.quote,
                chapter_index=chapter_index,
                chapter_title=chapter_title,
            ),
            references_event_id=referenced_event_id,
        )

        new_state.semantic.relationships[char_a_id][char_b_id].interactions.append(
            interaction
        )
        new_state.semantic.relationships[char_b_id][char_a_id].interactions.append(
            interaction
        )
        relationships_added += 1

    # -------------------------------------------------------------------------
    # 3. Process Event Extraction (FR-07)
    # -------------------------------------------------------------------------
    event_data = output.event_extraction
    events_added = 0

    for event_out in event_data.events:
        # Resolve character names to IDs
        involved_ids = []
        for name in event_out.involved_character_names:
            char_id = _resolve_character_id(new_state, name)
            if char_id:
                involved_ids.append(char_id)

        event = SignificantEvent(
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            description=event_out.description,
            involved_characters=involved_ids,
            evidence_quote=event_out.evidence_quote,
            significance=event_out.significance,
        )
        new_state.semantic.event_chronicle.append(event)
        events_added += 1

    # Process causal links
    for link_out in event_data.causal_links:
        # Try to find the referenced past event
        past_event = _find_event_by_description(
            new_state.semantic.event_chronicle, link_out.past_event_description
        )

        # Create the current event if it doesn't exist
        current_event = _find_event_by_description(
            new_state.semantic.event_chronicle, link_out.current_event_description
        )

        if past_event and current_event:
            causal_link = CausalLink(
                source_event_id=past_event.event_id,
                target_event_id=current_event.event_id,
                reasoning=link_out.reasoning,
                past_evidence_quote=link_out.past_evidence_quote,
                current_evidence_quote=link_out.current_evidence_quote,
            )
            new_state.semantic.causal_links.append(causal_link)

    # -------------------------------------------------------------------------
    # 4. Update Episodic Memory with Chapter Summary
    # -------------------------------------------------------------------------
    chapter_summary = ChapterSummary(
        index=chapter_index,
        title=chapter_title,
        summary=output.chapter_summary,
        characters_introduced=[
            c.id
            for c in new_state.semantic.characters.values()
            if c.first_appearance_chapter == chapter_index
        ],
        events_count=events_added,
        relationships_count=relationships_added,
    )
    new_state.semantic.chapter_summaries.append(chapter_summary)
    new_state.episodic.chapter_summaries.append(chapter_summary)

    # Update rolling window
    if chapter_index not in new_state.episodic.recent_chapter_indices:
        new_state.episodic.recent_chapter_indices.append(chapter_index)
        # Prune old chapters from window
        while (
            len(new_state.episodic.recent_chapter_indices)
            > new_state.episodic.window_size
        ):
            new_state.episodic.recent_chapter_indices.pop(0)
    while len(new_state.episodic.chapter_summaries) > new_state.episodic.window_size:
        new_state.episodic.chapter_summaries.pop(0)

    # -------------------------------------------------------------------------
    # 5. Update Resource Counters
    # -------------------------------------------------------------------------
    new_state.resource.llm_calls_made += 1
    new_state.resource.chapters_processed += 1

    # -------------------------------------------------------------------------
    # 6. Advance Workflow
    # -------------------------------------------------------------------------
    new_state.workflow.record_transition(
        to_stage=WorkflowStage.CHECK_COMPLETION,
        reason=f"Completed analysis of chapter {chapter_index + 1}",
    )

    return new_state


def skill_importance_scoring_handler(
    state: AgentState, output: ImportanceScoringOutput
) -> AgentState:
    """Handler for importance scoring that updates character scores (FR-05)."""
    new_state = deepcopy(state)

    for score_entry in output.scores:
        if score_entry.character_id in new_state.semantic.characters:
            new_state.semantic.characters[score_entry.character_id].importance_score = (
                score_entry.score
            )

    new_state.resource.llm_calls_made += 1

    new_state.workflow.record_transition(
        to_stage=WorkflowStage.GENERATE_REPORT,
        reason="Importance scoring completed",
    )

    return new_state


def advance_to_next_chapter(state: AgentState) -> AgentState:
    """Advance to the next chapter without mutating state in place (FR-03, FR-08)."""
    new_state = deepcopy(state)

    new_state.working.current_chapter_index += 1
    new_state.working.current_chapter_text = ""
    new_state.working.current_chapter_title = ""

    new_state.workflow.record_transition(
        to_stage=WorkflowStage.LOAD_CHAPTER,
        reason=f"Proceeding to chapter {new_state.working.current_chapter_index + 1}",
    )

    return new_state


# =============================================================================
# Tool Handlers
# =============================================================================


def update_state_from_tool(
    state: AgentState, tool: ToolName, output: BaseModel
) -> AgentState:
    """Route a structured tool output to its handler."""
    handler = _TOOL_HANDLERS.get(tool)
    if handler is None:
        raise ValueError(f"No handler registered for tool {tool}")
    return handler(state, output)


def tool_welcome_handler(state: AgentState, output: HelloWorldResponse) -> AgentState:
    """Example tool handler that updates the workflow state."""
    new_state = deepcopy(state)
    new_state.workflow.record_transition(
        to_stage=WorkflowStage.SEGMENTATION,
        reason="Initial welcome completed, proceeding to segmentation.",
    )
    return new_state


def tool_chapter_segmentation_handler(
    state: AgentState, output: ChapterSegmentationResult
) -> AgentState:
    """Handler for chapter segmentation that stores chapter map (FR-02)."""
    new_state = deepcopy(state)

    # Convert to our internal ChapterMetadata format
    chapter_map: List[ChapterMetadata] = []
    for ch in output.chapters:
        chapter_map.append(
            ChapterMetadata(
                index=ch.index,
                title=ch.title,
                book_index=ch.book_index,
                book_title=ch.book_title,
                chapter_number=ch.chapter_number,
                start_line=ch.start_line,
                end_line=ch.end_line,
                line_count=ch.line_count,
            )
        )

    book_map: List[BookMetadata] = []
    for book in output.books:
        book_chapters: List[ChapterMetadata] = [
            ChapterMetadata(
                index=ch.index,
                title=ch.title,
                book_index=ch.book_index,
                book_title=ch.book_title,
                chapter_number=ch.chapter_number,
                start_line=ch.start_line,
                end_line=ch.end_line,
                line_count=ch.line_count,
            )
            for ch in book.chapters
        ]
        book_map.append(
            BookMetadata(
                index=book.index,
                title=book.title,
                start_line=book.start_line,
                end_line=book.end_line,
                line_count=book.line_count,
                chapters=book_chapters,
            )
        )

    new_state.working.chapter_map = chapter_map
    new_state.working.total_chapters = output.total_chapters
    new_state.working.total_books = output.total_books
    new_state.working.book_map = book_map
    new_state.working.current_chapter_index = 0

    new_state.workflow.record_transition(
        to_stage=WorkflowStage.LOAD_CHAPTER,
        reason=f"Segmentation complete: {output.total_chapters} chapters detected",
    )

    return new_state


def tool_chapter_extraction_handler(
    state: AgentState, output: ChapterExtractionResult
) -> AgentState:
    """Handler for chapter extraction that loads chapter text (FR-01)."""
    new_state = deepcopy(state)

    new_state.working.current_chapter_text = output.text
    new_state.working.current_chapter_title = output.chapter_title
    new_state.working.current_chapter_index = output.chapter_index

    new_state.workflow.record_transition(
        to_stage=WorkflowStage.ANALYZE_CHAPTER,
        reason=f"Loaded chapter {output.chapter_index + 1}: {output.chapter_title}",
    )

    return new_state


def tool_html_report_handler(state: AgentState, output: HTMLReportResult) -> AgentState:
    """Handler for HTML report generation (FR-10, FR-11)."""
    new_state = deepcopy(state)

    new_state.workflow.record_transition(
        to_stage=WorkflowStage.COMPLETED,
        reason=f"Report generated: {len(output.files_generated)} files at {output.output_path}",
    )

    return new_state


# =============================================================================
# Helper Functions
# =============================================================================


def _resolve_character_id(state: AgentState, name: str) -> Optional[str]:
    """Resolve a character name or alias to its canonical ID."""
    name_lower = name.lower()

    # Check alias index first
    if name_lower in state.semantic.alias_index:
        return state.semantic.alias_index[name_lower]

    # Check canonical names
    for char_id, profile in state.semantic.characters.items():
        if profile.canonical_name.lower() == name_lower:
            return char_id

    return None


def _find_event_by_description(
    events: List[SignificantEvent], description: str
) -> Optional[SignificantEvent]:
    """Find an event by partial description match."""
    description_lower = description.lower()
    for event in events:
        if description_lower in event.description.lower():
            return event
    return None


# =============================================================================
# Handler Registries
# =============================================================================


_SKILL_HANDLERS: Dict[SkillName, SkillHandler] = {
    SkillName.ANALYZE_AND_PLAN: skill_analyze_and_plan_handler,  # type: ignore
    SkillName.ANALYZE_CHAPTER: skill_analyze_chapter_handler,  # type: ignore
    SkillName.IMPORTANCE_SCORING: skill_importance_scoring_handler,  # type: ignore
}

_TOOL_HANDLERS: Dict[ToolName, ToolHandler] = {
    ToolName.HELLO_WORLD: tool_welcome_handler,  # type: ignore
    ToolName.CHAPTER_SEGMENTATION: tool_chapter_segmentation_handler,  # type: ignore
    ToolName.CHAPTER_EXTRACTION: tool_chapter_extraction_handler,  # type: ignore
    ToolName.HTML_REPORT_GENERATION: tool_html_report_handler,  # type: ignore
}
