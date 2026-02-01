from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.engine.types import WorkflowStage

if TYPE_CHECKING:
    from src.tools.models import ChapterExtractionRequest, HelloWorldRequest


# =============================================================================
# Relationship Models (FR-09: Structured Relationship History)
# =============================================================================


class RelationshipEvidence(BaseModel):
    """Textual evidence supporting a relationship claim."""

    quote: str = Field(
        description="Verbatim quote from the text (1-3 sentences)",
        min_length=10,
    )
    chapter_index: int = Field(
        ge=0,
        description="Zero-based chapter index where quote appears",
    )
    chapter_title: str = Field(
        description="Title of the chapter for human readability",
    )


class RelationshipInteraction(BaseModel):
    """A single relationship entry (moment in time)."""

    interaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this interaction",
    )
    character_a_id: str = Field(description="UUID of first character")
    character_b_id: str = Field(description="UUID of second character")

    relation_type: str = Field(
        description="Nature of relationship (free-form, e.g., 'Secret Alliance')",
        min_length=3,
    )
    reasoning: str = Field(
        description="WHY this relationship exists - logical explanation",
        min_length=10,
    )
    context: str = Field(
        description="Brief situation/circumstances of the interaction",
        min_length=10,
    )
    evidence: RelationshipEvidence = Field(
        description="Textual proof with chapter reference",
    )

    extracted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when this entry was created",
    )

    # Cross-chapter causal links (FR-07)
    references_event_id: Optional[str] = Field(
        default=None,
        description="If this interaction references a past event, the event ID",
    )


class RelationshipHistory(BaseModel):
    """Complete history of interactions between two characters."""

    history_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this relationship pair",
    )
    character_a_id: str = Field(description="UUID of first character (canonical)")
    character_b_id: str = Field(description="UUID of second character (canonical)")
    interactions: List[RelationshipInteraction] = Field(
        default_factory=list,
        description="Chronological list of relationship moments",
    )

    @property
    def latest_relation_type(self) -> str:
        """Get the most recent relationship status."""
        if not self.interactions:
            return "Unknown"
        return self.interactions[-1].relation_type

    @property
    def first_interaction_chapter(self) -> int:
        """Chapter where these characters first interacted."""
        if not self.interactions:
            return -1
        return self.interactions[0].evidence.chapter_index


# =============================================================================
# Character Models (FR-04: Entity Resolution)
# =============================================================================


class CharacterProfile(BaseModel):
    """Canonical character entry in the knowledge graph."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this character",
    )
    canonical_name: str = Field(description="Primary name for this character")
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names/titles/references for this character",
    )
    first_appearance_chapter: int = Field(
        default=0,
        ge=0,
        description="Zero-based chapter index where character first appears",
    )
    description: str = Field(
        default="",
        description="Brief description of the character",
    )
    importance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 (background) to 1.0 (protagonist)",
    )


# =============================================================================
# Event Models (FR-07: Long-term Reasoning)
# =============================================================================


class SignificantEvent(BaseModel):
    """A major plot event stored for long-term reference."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this event",
    )
    chapter_index: int = Field(description="Chapter where event occurred")
    chapter_title: str = Field(description="Chapter title for display")
    description: str = Field(
        description="Brief summary of the event (1-2 sentences)",
    )
    involved_characters: List[str] = Field(
        default_factory=list,
        description="Character IDs of those involved",
    )
    evidence_quote: str = Field(description="Key quote demonstrating this event")
    significance: Literal["major", "moderate", "minor"] = Field(
        description="Narrative importance of this event",
    )


class CausalLink(BaseModel):
    """Links a current event to a past event with causal reasoning."""

    link_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this causal link",
    )
    source_event_id: str = Field(description="ID of the past event (cause)")
    target_event_id: str = Field(description="ID of the current event (effect)")
    reasoning: str = Field(
        description="Explanation of how the past event caused the current event",
    )
    past_evidence_quote: str = Field(
        description="Quote from the past chapter supporting the cause",
    )
    current_evidence_quote: str = Field(
        description="Quote from the current chapter supporting the effect",
    )


# =============================================================================
# Chapter Metadata Models (FR-01, FR-02)
# =============================================================================


class ChapterMetadata(BaseModel):
    """Metadata for a single chapter."""

    index: int = Field(description="Zero-based chapter index")
    title: str = Field(description="Chapter title/header text")
    book_index: int = Field(description="Zero-based book index containing chapter")
    book_title: str = Field(description="Book title/header text")
    chapter_number: int = Field(
        description="1-based chapter number within the containing book"
    )
    start_line: int = Field(description="1-based line number where chapter starts")
    end_line: int = Field(description="1-based line number where chapter ends")
    line_count: int = Field(description="Total lines in this chapter")


class BookMetadata(BaseModel):
    """Metadata for a single book containing chapters."""

    index: int = Field(description="Zero-based book index")
    title: str = Field(description="Book title/header text")
    start_line: int = Field(description="1-based line number where book starts")
    end_line: int = Field(description="1-based line number where book ends")
    line_count: int = Field(description="Total lines in this book section")
    chapters: List[ChapterMetadata] = Field(
        default_factory=list,
        description="Chapters that belong to this book",
    )


class ChapterSummary(BaseModel):
    """Summary information about a processed chapter."""

    index: int = Field(description="Zero-based chapter index")
    title: str = Field(description="Chapter title")
    summary: str = Field(default="", description="Brief summary of the chapter")
    characters_introduced: List[str] = Field(
        default_factory=list,
        description="Character IDs introduced in this chapter",
    )
    events_count: int = Field(
        default=0,
        description="Number of significant events in this chapter",
    )
    relationships_count: int = Field(
        default=0,
        description="Number of relationships extracted in this chapter",
    )


# =============================================================================
# Memory Layer Models
# =============================================================================


class ConstitutionalMemory(BaseModel):
    """The 'agent's DNA.' Security and ethical principles (Guardrails)."""

    persona: str = Field(
        default="You are an expert literary analyst specializing in character "
        "relationships and narrative structure.",
        description="The agent's persona and role",
    )


class WorkingMemory(BaseModel):
    """The context of the current session (RAM). 'Right now.'"""

    query_analysis: Optional[Any] = Field(
        default=None,
        description="Analysis and plan of the current query.",
    )
    # FR-01: High Volume Support - Chapter progress tracking
    current_chapter_index: int = Field(
        default=0,
        description="Current chapter being processed (zero-based)",
    )
    total_chapters: int = Field(
        default=0,
        description="Total number of chapters in the book",
    )
    total_books: int = Field(
        default=0,
        description="Total number of books in the text",
    )
    current_chapter_text: str = Field(
        default="",
        description="Text content of the current chapter",
    )
    current_chapter_title: str = Field(
        default="",
        description="Title of the current chapter",
    )
    # Book metadata
    source_file_path: str = Field(
        default="",
        description="Path to the source text file",
    )
    book_title: str = Field(
        default="",
        description="Title of the book being analyzed",
    )
    # Chapter segmentation results
    chapter_map: List[ChapterMetadata] = Field(
        default_factory=list,
        description="List of all chapter boundaries",
    )
    book_map: List[BookMetadata] = Field(
        default_factory=list,
        description="List of all books with nested chapters",
    )


class WorkflowTransition(BaseModel):
    """Record of a workflow stage transition."""

    from_stage: WorkflowStage
    to_stage: WorkflowStage
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: Optional[str] = None


class WorkflowMemory(BaseModel):
    """The State Machine. Where am I in the business process?"""

    current_stage: WorkflowStage = Field(
        default=WorkflowStage.INITIAL,
        description="Current stage in the workflow",
    )
    goal: str = Field(..., description="The initial goal that started the workflow.")
    history: List[WorkflowTransition] = Field(
        default_factory=list,
        description="Historical record of stage transitions.",
    )

    def record_transition(
        self, to_stage: WorkflowStage, reason: Optional[str] = None
    ) -> None:
        """Helper to append a transition to history if the stage changed."""
        if self.current_stage != to_stage:
            self.history.append(
                WorkflowTransition(
                    from_stage=self.current_stage, to_stage=to_stage, reason=reason
                )
            )
            self.current_stage = to_stage


class EpisodicMemory(BaseModel):
    """What happened? Interaction history, event logs (short-term)."""

    # FR-08: Rolling window of recent chapters
    raw_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Unprocessed events from recent chapters",
    )
    recent_chapter_indices: List[int] = Field(
        default_factory=list,
        description="Indices of chapters in the rolling window",
    )
    window_size: int = Field(
        default=5,
        description="Number of recent chapters to retain full details for",
    )
    chapter_summaries: List[ChapterSummary] = Field(
        default_factory=list,
        description="Summaries of processed chapters",
    )


class SemanticMemory(BaseModel):
    """What do I know? The knowledge base (cumulative)."""

    # FR-04: Character Registry with Entity Resolution
    characters: Dict[str, CharacterProfile] = Field(
        default_factory=dict,
        description="Character ID -> Profile mapping",
    )
    alias_index: Dict[str, str] = Field(
        default_factory=dict,
        description="Alias/name -> Character ID mapping for quick lookup",
    )

    # FR-06: Relationship Graph with Full Attribution
    # Nested map: character_id -> {other_character_id -> RelationshipHistory}
    relationships: Dict[str, Dict[str, RelationshipHistory]] = Field(
        default_factory=dict,
        description="Nested relationship map by character",
    )

    # FR-07: Event Chronicle for Long-term Reasoning
    event_chronicle: List[SignificantEvent] = Field(
        default_factory=list,
        description="Timeline of major events across all chapters",
    )
    causal_links: List[CausalLink] = Field(
        default_factory=list,
        description="Cause-and-effect links between events",
    )
    chapter_summaries: List[ChapterSummary] = Field(
        default_factory=list,
        description="Cumulative summaries for all processed chapters",
    )


class ProceduralMemory(BaseModel):
    """How do I do it? Tool definitions, APIs, user manuals."""

    available_tools: List[str] = Field(
        default_factory=list,
        description="List of available tool names",
    )


class ResourceMemory(BaseModel):
    """Do I have the resources? System status, API availability, limits."""

    llm_calls_made: int = Field(
        default=0,
        description="Number of LLM API calls made in this session",
    )
    chapters_processed: int = Field(
        default=0,
        description="Number of chapters successfully processed",
    )


# =============================================================================
# Root State Model
# =============================================================================


class AgentState(BaseModel):
    """Full memory object available to the engine layer."""

    core: ConstitutionalMemory
    working: WorkingMemory
    workflow: WorkflowMemory
    episodic: EpisodicMemory
    semantic: SemanticMemory
    procedural: ProceduralMemory
    resource: ResourceMemory

    def get_hello_world_request(self) -> "HelloWorldRequest":
        """Constructs a HelloWorldRequest from the agent state."""
        from src.tools.models import HelloWorldRequest

        return HelloWorldRequest(query="Hello, World!")

    def get_chapter_extraction_request(self) -> "ChapterExtractionRequest":
        """Constructs a ChapterExtractionRequest for the current chapter."""
        from src.tools.models import ChapterExtractionRequest

        return ChapterExtractionRequest(
            file_path=self.working.source_file_path,
            chapter_index=self.working.current_chapter_index,
            chapter_map=self.working.chapter_map,
        )

    def get_relationship_key(self, char_a_id: str, char_b_id: str) -> str:
        """Generate a consistent key for a relationship pair."""
        return "::".join(sorted([char_a_id, char_b_id]))
