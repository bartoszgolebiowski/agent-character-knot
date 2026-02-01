from __future__ import annotations

from pathlib import Path

from src.memory.models import (
    AgentState,
    CharacterProfile,
    ChapterSummary,
    RelationshipEvidence,
    RelationshipHistory,
    RelationshipInteraction,
    SemanticMemory,
    SignificantEvent,
)
from src.memory.state_manager import create_initial_state
from src.tools.html_report_generator import HTMLReportGeneratorTool
from src.tools.models import HTMLReportRequest


def _build_state() -> AgentState:
    state = create_initial_state(goal="test", source_file_path="", book_title="Test")

    alice = CharacterProfile(
        canonical_name="Alice",
        aliases=["A"],
        first_appearance_chapter=0,
        description="Protagonist",
    )
    bob = CharacterProfile(
        canonical_name="Bob",
        aliases=["B"],
        first_appearance_chapter=0,
        description="Friend",
    )

    state.semantic.characters[alice.id] = alice
    state.semantic.characters[bob.id] = bob
    state.semantic.alias_index["alice"] = alice.id
    state.semantic.alias_index["bob"] = bob.id

    interaction = RelationshipInteraction(
        character_a_id=alice.id,
        character_b_id=bob.id,
        relation_type="Allies",
        reasoning="They agreed to help each other.",
        context="Met in town square.",
        evidence=RelationshipEvidence(
            quote="We stand together.",
            chapter_index=0,
            chapter_title="Chapter 1",
        ),
    )

    history_ab = RelationshipHistory(
        character_a_id=alice.id,
        character_b_id=bob.id,
        interactions=[interaction],
    )
    history_ba = RelationshipHistory(
        character_a_id=bob.id,
        character_b_id=alice.id,
        interactions=[interaction],
    )

    state.semantic.relationships[alice.id] = {bob.id: history_ab}
    state.semantic.relationships[bob.id] = {alice.id: history_ba}

    event = SignificantEvent(
        chapter_index=0,
        chapter_title="Chapter 1",
        description="Alice meets Bob.",
        involved_characters=[alice.id, bob.id],
        evidence_quote="Alice greeted Bob.",
        significance="major",
    )
    state.semantic.event_chronicle.append(event)

    chapter_summary = ChapterSummary(
        index=0,
        title="Chapter 1",
        summary="Alice meets Bob.",
        characters_introduced=[alice.id, bob.id],
        events_count=1,
        relationships_count=1,
    )
    state.semantic.chapter_summaries.append(chapter_summary)
    state.episodic.chapter_summaries.append(chapter_summary)

    return state


def test_html_report_generator_creates_files(tmp_path: Path) -> None:
    state = _build_state()
    tool = HTMLReportGeneratorTool()

    result = tool.generate(
        HTMLReportRequest(
            output_directory=str(tmp_path),
            report_title="Test Report",
            book_title="Test Book",
        ),
        state,
    )

    index_path = Path(result.index_file)
    assert index_path.exists()
    assert (tmp_path / "styles.css").exists()

    character_files = [p for p in result.files_generated if "character-" in p]
    chapter_files = [p for p in result.files_generated if "chapter-" in p]

    assert len(character_files) == 2
    assert len(chapter_files) == 1

    index_html = index_path.read_text(encoding="utf-8")
    assert "character-" in index_html
    assert "chapter-000.html" in index_html


def test_chapter_navigation_has_no_next_on_last(tmp_path: Path) -> None:
    state = _build_state()
    tool = HTMLReportGeneratorTool()

    tool.generate(
        HTMLReportRequest(
            output_directory=str(tmp_path),
            report_title="Test Report",
            book_title="Test Book",
        ),
        state,
    )

    chapter_html = (tmp_path / "chapter-000.html").read_text(encoding="utf-8")
    assert "Next Chapter" not in chapter_html
