from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from .models import HTMLReportRequest, HTMLReportResult

if TYPE_CHECKING:
    from src.memory.models import AgentState


@dataclass(frozen=True, slots=True)
class HTMLReportGeneratorTool:
    """Generates multi-page HTML report from semantic memory (FR-10, FR-11)."""

    template_directory: str = "src/prompting/jinja/report"

    def generate(
        self, request: HTMLReportRequest, state: "AgentState"
    ) -> HTMLReportResult:
        """Generate the complete HTML report."""
        output_dir = Path(request.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        env = self._setup_jinja_environment(state)

        generated_files: List[str] = []

        index_file = self._generate_index_page(
            env=env,
            output_dir=output_dir,
            request=request,
            state=state,
        )
        generated_files.append(index_file)

        character_files = self._generate_character_pages(
            env=env,
            output_dir=output_dir,
            state=state,
        )
        generated_files.extend(character_files)

        chapter_files = self._generate_chapter_pages(
            env=env,
            output_dir=output_dir,
            state=state,
        )
        generated_files.extend(chapter_files)

        css_file = self._generate_stylesheet(env, output_dir)
        generated_files.append(css_file)

        return HTMLReportResult(
            output_path=str(output_dir),
            files_generated=generated_files,
            index_file=index_file,
            total_characters=len(state.semantic.characters),
            total_chapters=len(state.semantic.chapter_summaries),
        )

    def _setup_jinja_environment(self, state: "AgentState") -> Environment:
        template_path = Path(self.template_directory)
        template_path.mkdir(parents=True, exist_ok=True)

        env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=True,
        )

        def character_link(char_id: str, text: str | None = None) -> Markup:
            if char_id not in state.semantic.characters:
                return Markup(f"[Unknown: {char_id}]")
            char = state.semantic.characters[char_id]
            display_text = text or char.canonical_name
            return Markup(f'<a href="character-{char_id}.html">{display_text}</a>')

        def chapter_link(chapter_index: int, text: str | None = None) -> Markup:
            chapter_file = f"chapter-{chapter_index:03d}.html"
            summaries = state.semantic.chapter_summaries
            chapter_meta = next(
                (c for c in summaries if c.index == chapter_index),
                None,
            )
            display_text = text or (
                chapter_meta.title if chapter_meta else f"Chapter {chapter_index + 1}"
            )
            return Markup(f'<a href="{chapter_file}">{display_text}</a>')

        def character_name(char_id: str) -> str:
            if char_id in state.semantic.characters:
                return state.semantic.characters[char_id].canonical_name
            return "Unknown"

        def importance_stars(score: float) -> str:
            full_stars = int(score * 5)
            empty_stars = 5 - full_stars
            return "★" * full_stars + "☆" * empty_stars

        env.filters["character_link"] = character_link
        env.filters["chapter_link"] = chapter_link
        env.filters["character_name"] = character_name
        env.filters["importance_stars"] = importance_stars

        return env

    def _generate_index_page(
        self,
        *,
        env: Environment,
        output_dir: Path,
        request: HTMLReportRequest,
        state: "AgentState",
    ) -> str:
        sorted_characters = sorted(
            state.semantic.characters.values(),
            key=lambda c: c.importance_score,
            reverse=True,
        )

        chapters = state.semantic.chapter_summaries
        relationship_pairs: set[tuple[str, str]] = set()
        for char_id, rels in state.semantic.relationships.items():
            for other_id in rels.keys():
                if char_id < other_id:
                    relationship_pairs.add((char_id, other_id))

        content = self._render_index_template(
            env=env,
            report_title=request.report_title,
            book_title=request.book_title,
            characters=sorted_characters,
            chapters=chapters,
            total_relationships=len(relationship_pairs),
            total_events=len(state.semantic.event_chronicle),
        )

        output_path = output_dir / "index.html"
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)

    def _generate_character_pages(
        self,
        *,
        env: Environment,
        output_dir: Path,
        state: "AgentState",
    ) -> List[str]:
        generated_files: List[str] = []
        events_by_id = {e.event_id: e for e in state.semantic.event_chronicle}

        for char_id, profile in state.semantic.characters.items():
            char_relationships = state.semantic.relationships.get(char_id, {})

            content = self._render_character_template(
                env=env,
                profile=profile,
                relationships=char_relationships,
                all_characters=state.semantic.characters,
                events_by_id=events_by_id,
            )

            output_path = output_dir / f"character-{char_id}.html"
            output_path.write_text(content, encoding="utf-8")
            generated_files.append(str(output_path))

        return generated_files

    def _generate_chapter_pages(
        self,
        *,
        env: Environment,
        output_dir: Path,
        state: "AgentState",
    ) -> List[str]:
        generated_files: List[str] = []

        for chapter_summary in state.semantic.chapter_summaries:
            chapter_events = [
                e
                for e in state.semantic.event_chronicle
                if e.chapter_index == chapter_summary.index
            ]

            chapter_relationships = []
            seen_pairs: set[str] = set()
            for char_id, rels in state.semantic.relationships.items():
                for other_id, rel_history in rels.items():
                    pair_key = "::".join(sorted([char_id, other_id]))
                    if pair_key in seen_pairs:
                        continue
                    for interaction in rel_history.interactions:
                        if interaction.evidence.chapter_index == chapter_summary.index:
                            chapter_relationships.append(interaction)
                            seen_pairs.add(pair_key)
                            break

            content = self._render_chapter_template(
                env=env,
                chapter=chapter_summary,
                events=chapter_events,
                relationships=chapter_relationships,
                all_characters=state.semantic.characters,
                total_chapters=len(state.semantic.chapter_summaries),
            )

            output_path = output_dir / f"chapter-{chapter_summary.index:03d}.html"
            output_path.write_text(content, encoding="utf-8")
            generated_files.append(str(output_path))

        return generated_files

    def _generate_stylesheet(self, env: Environment, output_dir: Path) -> str:
        template = env.get_template("styles.css.j2")
        css_content = template.render()
        output_path = output_dir / "styles.css"
        output_path.write_text(css_content, encoding="utf-8")
        return str(output_path)

    def _render_index_template(
        self,
        *,
        env: Environment,
        report_title: str,
        book_title: str,
        characters: list,
        chapters: list,
        total_relationships: int,
        total_events: int,
    ) -> str:
        template = env.get_template("index.html.j2")
        return template.render(
            report_title=report_title,
            book_title=book_title,
            characters=characters,
            chapters=chapters,
            total_relationships=total_relationships,
            total_events=total_events,
        )

    def _render_character_template(
        self,
        *,
        env: Environment,
        profile,
        relationships: dict,
        all_characters: dict,
        events_by_id: dict,
    ) -> str:
        template = env.get_template("character.html.j2")
        return template.render(
            character=profile,
            relationships=relationships,
            all_characters=all_characters,
            events_by_id=events_by_id,
        )

    def _render_chapter_template(
        self,
        *,
        env: Environment,
        chapter,
        events: list,
        relationships: list,
        all_characters: dict,
        total_chapters: int,
    ) -> str:
        template = env.get_template("chapter.html.j2")
        return template.render(
            chapter=chapter,
            events=events,
            relationships=relationships,
            all_characters=all_characters,
            total_chapters=total_chapters,
        )
