from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.engine.types import WorkflowStage


# =============================================================================
# Analyze and Plan Skill Output
# =============================================================================


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


# =============================================================================
# Entity Resolution Skill Output (FR-04)
# =============================================================================


class MentionedCharacter(BaseModel):
    """A character mentioned in the current chapter."""

    name: str = Field(description="Name or reference as it appears in text")
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence that this is a real character (not a background extra)",
    )
    description: str = Field(
        default="",
        description="Brief description of the character based on context",
    )


class AliasMapping(BaseModel):
    """Maps a new alias to an existing canonical character."""

    alias: str = Field(description="The new mention/name found in text")
    canonical_id: Optional[str] = Field(
        default=None,
        description="UUID of existing character, or null if new character",
    )
    canonical_name: Optional[str] = Field(
        default=None,
        description="Name of the canonical character for reference",
    )
    reasoning: str = Field(
        description="Why this alias belongs to this character (or why it's new)",
    )


class NewCharacterEntry(BaseModel):
    """Entry for a newly discovered character."""

    suggested_canonical_name: str = Field(
        description="Suggested primary name for this character",
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Any aliases already known for this character",
    )
    description: str = Field(
        default="",
        description="Brief description of the character",
    )


class EntityResolutionOutput(BaseModel):
    """Result of entity resolution for a chapter."""

    mentioned_characters: List[MentionedCharacter] = Field(
        default_factory=list,
        description="All character mentions found in the chapter",
    )
    alias_mappings: List[AliasMapping] = Field(
        default_factory=list,
        description="List of alias-to-canonical mappings",
    )
    new_characters: List[NewCharacterEntry] = Field(
        default_factory=list,
        description="New characters to add to the registry",
    )


# =============================================================================
# Relationship Extraction Skill Output (FR-06)
# =============================================================================


class RelationshipEvidenceOutput(BaseModel):
    """Textual evidence supporting a relationship claim."""

    quote: str = Field(
        description="Verbatim quote from the text (1-3 sentences)",
    )


class RelationshipInteractionOutput(BaseModel):
    """A single relationship entry from extraction."""

    character_a_name: str = Field(
        description="Name of first character as mentioned in text",
    )
    character_b_name: str = Field(
        description="Name of second character as mentioned in text",
    )
    relation_type: str = Field(
        description="Nature of relationship (e.g., 'Secret Alliance', 'Bitter Enemies')",
    )
    reasoning: str = Field(
        description="WHY this relationship exists - logical explanation",
    )
    context: str = Field(
        description="Brief situation/circumstances of the interaction",
    )
    evidence: RelationshipEvidenceOutput = Field(
        description="Textual proof from the chapter",
    )
    references_past_event: Optional[str] = Field(
        default=None,
        description="If this interaction references a past event, describe it briefly",
    )
    is_causal_node: bool = Field(
        default=False,
        description="True if this interaction creates a persistent causal node",
    )
    resolves_causal_node_id: Optional[str] = Field(
        default=None,
        description="Interaction ID of a prior causal node resolved here, if any",
    )
    causal_reasoning: Optional[str] = Field(
        default=None,
        description="Explanation for the causal connection, if applicable",
    )


class RelationshipExtractionOutput(BaseModel):
    """Result of relationship extraction for a chapter."""

    interactions: List[RelationshipInteractionOutput] = Field(
        default_factory=list,
        description="All relationship moments detected in this chapter",
    )


# =============================================================================
# Event Extraction Skill Output (FR-07)
# =============================================================================


class SignificantEventOutput(BaseModel):
    """A significant event extracted from a chapter."""

    description: str = Field(
        description="Brief summary of the event (1-2 sentences)",
    )
    involved_character_names: List[str] = Field(
        default_factory=list,
        description="Names of characters involved in this event",
    )
    evidence_quote: str = Field(
        description="Key quote demonstrating this event",
    )
    significance: Literal["major", "moderate", "minor"] = Field(
        description="Narrative importance of this event",
    )


class CausalLinkOutput(BaseModel):
    """A detected causal link between events."""

    past_event_description: str = Field(
        description="Description of the past event being referenced",
    )
    current_event_description: str = Field(
        description="Description of the current event",
    )
    reasoning: str = Field(
        description="Explanation of the cause-and-effect relationship",
    )
    past_evidence_quote: str = Field(
        description="Quote from the past chapter (if remembered)",
    )
    current_evidence_quote: str = Field(
        description="Quote from the current chapter",
    )


class EventExtractionOutput(BaseModel):
    """Result of event extraction for a chapter."""

    events: List[SignificantEventOutput] = Field(
        default_factory=list,
        description="Significant events from this chapter",
    )
    causal_links: List[CausalLinkOutput] = Field(
        default_factory=list,
        description="Detected links to past events",
    )


# =============================================================================
# Importance Scoring Skill Output (FR-05)
# =============================================================================


class CharacterImportanceScore(BaseModel):
    """Importance assessment for a single character."""

    character_id: str = Field(description="UUID of the character")
    character_name: str = Field(description="Canonical name of the character")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 (background) to 1.0 (protagonist)",
    )
    reasoning: str = Field(
        description="Brief explanation of why this score was assigned",
    )


class ImportanceScoringOutput(BaseModel):
    """Result of importance scoring for all characters."""

    scores: List[CharacterImportanceScore] = Field(
        description="Importance scores for all characters",
    )


# =============================================================================
# Chapter Analysis Combined Skill Output
# =============================================================================


# =============================================================================
# Character Dossier Updates (FR-12)
# =============================================================================


class CharacterDossierUpdate(BaseModel):
    """Update entry for a character dossier."""

    character_name: str = Field(
        description="Character name or alias as referenced in this chapter",
    )
    identity: Optional[str] = Field(
        default=None,
        description="Concise identity summary",
    )
    core_traits: List[str] = Field(
        default_factory=list,
        description="Traits that should be added or reinforced",
    )
    current_goals: List[str] = Field(
        default_factory=list,
        description="Current goals or motivations",
    )
    evolution_summary: Optional[str] = Field(
        default=None,
        description="Short update to append to the evolution summary",
    )
    last_known_location: Optional[str] = Field(
        default=None,
        description="Most recent location, if mentioned",
    )


# =============================================================================
# Chapter Analysis Combined Skill Output
# =============================================================================


class ChapterAnalysisOutput(BaseModel):
    """Combined output from analyzing a single chapter."""

    chapter_summary: str = Field(
        default="",
        description="Brief summary of the chapter's main events",
    )
    entity_resolution: EntityResolutionOutput = Field(
        default_factory=EntityResolutionOutput,
        description="Character and alias resolution results",
    )
    relationship_extraction: RelationshipExtractionOutput = Field(
        default_factory=RelationshipExtractionOutput,
        description="Extracted relationships from this chapter",
    )
    event_extraction: EventExtractionOutput = Field(
        default_factory=EventExtractionOutput,
        description="Significant events from this chapter",
    )
    dossier_updates: List[CharacterDossierUpdate] = Field(
        default_factory=list,
        description="Refined dossier updates for characters in this chapter",
    )


# =============================================================================
# Memory Consolidation Output (FR-13)
# =============================================================================


class ConsolidatedMemoryOutput(BaseModel):
    """Consolidated summary for a group of chapters."""

    summary: str = Field(
        description="Single cohesive summary covering the provided chapters",
    )
