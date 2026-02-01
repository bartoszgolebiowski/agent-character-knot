from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List

from jinja2 import Environment, FileSystemLoader

from .models import HTMLReportRequest, HTMLReportResult

if TYPE_CHECKING:
    from src.memory.models import AgentState


@dataclass(frozen=True, slots=True)
class HTMLReportGeneratorTool:
    """Generates multi-page HTML report from semantic memory (FR-10, FR-11).

    Creates an interconnected set of HTML files:
    - index.html: Main landing page with character/chapter lists
    - character-{id}.html: One page per character
    - chapter-{index:03d}.html: One page per chapter
    """

    template_directory: str = "src/prompting/jinja/report"

    def generate(
        self, request: HTMLReportRequest, state: "AgentState"
    ) -> HTMLReportResult:
        """Generate the complete HTML report.

        Args:
            request: Configuration for report generation
            state: AgentState containing all extracted data

        Returns:
            HTMLReportResult with list of generated files
        """
        output_dir = Path(request.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2 environment with custom filters
        env = self._setup_jinja_environment(state)

        generated_files: List[str] = []

        # Generate index page
        index_file = self._generate_index_page(
            env=env,
            output_dir=output_dir,
            request=request,
            state=state,
        )
        generated_files.append(index_file)

        # Generate character pages
        character_files = self._generate_character_pages(
            env=env,
            output_dir=output_dir,
            state=state,
        )
        generated_files.extend(character_files)

        # Generate chapter pages
        chapter_files = self._generate_chapter_pages(
            env=env,
            output_dir=output_dir,
            state=state,
        )
        generated_files.extend(chapter_files)

        # Copy/generate CSS
        css_file = self._generate_stylesheet(output_dir)
        generated_files.append(css_file)

        return HTMLReportResult(
            output_path=str(output_dir),
            files_generated=generated_files,
            index_file=index_file,
            total_characters=len(state.semantic.characters),
            total_chapters=len(state.episodic.chapter_summaries),
        )

    def _setup_jinja_environment(self, state: "AgentState") -> Environment:
        """Configure Jinja2 with custom filters for hyperlinking (FR-11)."""
        template_path = Path(self.template_directory)

        # Create template directory if it doesn't exist
        template_path.mkdir(parents=True, exist_ok=True)

        env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=True,
        )

        # Custom filter: Generate hyperlink to character page
        def character_link(char_id: str, text: str | None = None) -> str:
            """Generate hyperlink to character page."""
            if char_id not in state.semantic.characters:
                return f"[Unknown: {char_id}]"

            char = state.semantic.characters[char_id]
            display_text = text or char.canonical_name
            return f'<a href="character-{char_id}.html">{display_text}</a>'

        # Custom filter: Generate hyperlink to chapter page
        def chapter_link(chapter_index: int, text: str | None = None) -> str:
            """Generate hyperlink to chapter page."""
            chapter_file = f"chapter-{chapter_index:03d}.html"

            # Find chapter metadata for title
            summaries = state.episodic.chapter_summaries
            chapter_meta = next(
                (c for c in summaries if c.index == chapter_index),
                None,
            )

            display_text = text or (
                chapter_meta.title if chapter_meta else f"Chapter {chapter_index + 1}"
            )

            return f'<a href="{chapter_file}">{display_text}</a>'

        # Custom filter: Get character name from ID
        def character_name(char_id: str) -> str:
            """Get character canonical name."""
            if char_id in state.semantic.characters:
                return state.semantic.characters[char_id].canonical_name
            return "Unknown"

        # Custom filter: Format importance score as stars
        def importance_stars(score: float) -> str:
            """Convert importance score to star rating."""
            full_stars = int(score * 5)
            empty_stars = 5 - full_stars
            return "★" * full_stars + "☆" * empty_stars

        # Register filters
        env.filters["character_link"] = character_link
        env.filters["chapter_link"] = chapter_link
        env.filters["character_name"] = character_name
        env.filters["importance_stars"] = importance_stars

        return env

    def _generate_index_page(
        self,
        env: Environment,
        output_dir: Path,
        request: HTMLReportRequest,
        state: "AgentState",
    ) -> str:
        """Generate the main index.html page."""
        # Sort characters by importance score (descending)
        sorted_characters = sorted(
            state.semantic.characters.values(),
            key=lambda c: c.importance_score,
            reverse=True,
        )

        # Get chapter summaries
        chapters = state.episodic.chapter_summaries

        content = self._render_index_template(
            report_title=request.report_title,
            book_title=request.book_title,
            characters=sorted_characters,
            chapters=chapters,
            total_relationships=len(state.semantic.relationships),
            total_events=len(state.semantic.event_chronicle),
        )

        output_path = output_dir / "index.html"
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)

    def _generate_character_pages(
        self,
        env: Environment,
        output_dir: Path,
        state: "AgentState",
    ) -> List[str]:
        """Generate one HTML page per character."""
        generated_files: List[str] = []

        for char_id, profile in state.semantic.characters.items():
            # Find all relationships involving this character
            char_relationships = []
            for rel_key, rel_history in state.semantic.relationships.items():
                if char_id in rel_key:
                    char_relationships.append(rel_history)

            content = self._render_character_template(
                profile=profile,
                relationships=char_relationships,
                all_characters=state.semantic.characters,
            )

            output_path = output_dir / f"character-{char_id}.html"
            output_path.write_text(content, encoding="utf-8")
            generated_files.append(str(output_path))

        return generated_files

    def _generate_chapter_pages(
        self,
        env: Environment,
        output_dir: Path,
        state: "AgentState",
    ) -> List[str]:
        """Generate one HTML page per chapter."""
        generated_files: List[str] = []

        for chapter_summary in state.episodic.chapter_summaries:
            # Find events for this chapter
            chapter_events = [
                e
                for e in state.semantic.event_chronicle
                if e.chapter_index == chapter_summary.index
            ]

            # Find relationships introduced in this chapter
            chapter_relationships = []
            for rel_history in state.semantic.relationships.values():
                for interaction in rel_history.interactions:
                    if interaction.evidence.chapter_index == chapter_summary.index:
                        chapter_relationships.append(interaction)
                        break  # Only add once per relationship pair

            content = self._render_chapter_template(
                chapter=chapter_summary,
                events=chapter_events,
                relationships=chapter_relationships,
                all_characters=state.semantic.characters,
            )

            output_path = output_dir / f"chapter-{chapter_summary.index:03d}.html"
            output_path.write_text(content, encoding="utf-8")
            generated_files.append(str(output_path))

        return generated_files

    def _generate_stylesheet(self, output_dir: Path) -> str:
        """Generate the CSS stylesheet."""
        css_content = """
/* StoryGraph Report Stylesheet */
:root {
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --accent-color: #e74c3c;
    --background-color: #ecf0f1;
    --text-color: #2c3e50;
    --border-color: #bdc3c7;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Georgia', serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

header {
    background-color: var(--primary-color);
    color: white;
    padding: 20px;
    margin-bottom: 30px;
    border-radius: 8px;
}

header h1 {
    margin-bottom: 5px;
}

header .subtitle {
    opacity: 0.8;
    font-style: italic;
}

nav {
    background-color: white;
    padding: 15px;
    margin-bottom: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

nav a {
    color: var(--secondary-color);
    text-decoration: none;
    margin-right: 20px;
}

nav a:hover {
    text-decoration: underline;
}

main {
    background-color: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h2 {
    color: var(--primary-color);
    border-bottom: 2px solid var(--secondary-color);
    padding-bottom: 10px;
    margin-bottom: 20px;
}

h3 {
    color: var(--secondary-color);
    margin-top: 25px;
    margin-bottom: 15px;
}

.character-card, .chapter-card {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
}

.character-card:hover, .chapter-card:hover {
    border-color: var(--secondary-color);
}

.importance-score {
    color: gold;
    font-size: 1.2em;
}

.aliases {
    color: #7f8c8d;
    font-style: italic;
    margin-top: 5px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

th, td {
    border: 1px solid var(--border-color);
    padding: 12px;
    text-align: left;
}

th {
    background-color: var(--primary-color);
    color: white;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

tr:hover {
    background-color: #f1f1f1;
}

.quote {
    background-color: #f9f9f9;
    border-left: 4px solid var(--secondary-color);
    padding: 15px;
    margin: 15px 0;
    font-style: italic;
}

.quote .attribution {
    text-align: right;
    margin-top: 10px;
    font-size: 0.9em;
    color: #7f8c8d;
}

.relationship-history {
    margin-top: 20px;
}

.interaction {
    border-left: 3px solid var(--accent-color);
    padding-left: 15px;
    margin-bottom: 20px;
}

.interaction-type {
    font-weight: bold;
    color: var(--accent-color);
}

.event-card {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
}

.significance-major {
    border-left: 4px solid var(--accent-color);
}

.significance-moderate {
    border-left: 4px solid var(--secondary-color);
}

.significance-minor {
    border-left: 4px solid var(--border-color);
}

a {
    color: var(--secondary-color);
}

a:hover {
    color: var(--accent-color);
}

footer {
    margin-top: 30px;
    text-align: center;
    color: #7f8c8d;
    font-size: 0.9em;
}
"""
        output_path = output_dir / "styles.css"
        output_path.write_text(css_content, encoding="utf-8")
        return str(output_path)

    def _render_index_template(
        self,
        report_title: str,
        book_title: str,
        characters: list,
        chapters: list,
        total_relationships: int,
        total_events: int,
    ) -> str:
        """Render the index page HTML."""
        character_rows = ""
        for char in characters:
            stars = "★" * int(char.importance_score * 5) + "☆" * (
                5 - int(char.importance_score * 5)
            )
            aliases = ", ".join(char.aliases) if char.aliases else "-"
            character_rows += f"""
            <tr>
                <td><a href="character-{char.id}.html">{char.canonical_name}</a></td>
                <td class="importance-score">{stars}</td>
                <td class="aliases">{aliases}</td>
                <td>Chapter {char.first_appearance_chapter + 1}</td>
            </tr>
            """

        chapter_rows = ""
        for chap in chapters:
            chapter_rows += f"""
            <tr>
                <td><a href="chapter-{chap.index:03d}.html">{chap.title}</a></td>
                <td>{chap.characters_introduced or 0} new</td>
                <td>{chap.events_count}</td>
                <td>{chap.relationships_count}</td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>{report_title}</h1>
        <p class="subtitle">Analysis of "{book_title}"</p>
    </header>

    <nav>
        <a href="index.html">Home</a>
        <a href="#characters">Characters ({len(characters)})</a>
        <a href="#chapters">Chapters ({len(chapters)})</a>
    </nav>

    <main>
        <section>
            <h2>Summary</h2>
            <p>This report contains analysis of <strong>{len(characters)}</strong> characters,
            <strong>{total_relationships}</strong> relationship connections, and
            <strong>{total_events}</strong> significant events across
            <strong>{len(chapters)}</strong> chapters.</p>
        </section>

        <section id="characters">
            <h2>Characters</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Importance</th>
                        <th>Also Known As</th>
                        <th>First Appearance</th>
                    </tr>
                </thead>
                <tbody>
                    {character_rows}
                </tbody>
            </table>
        </section>

        <section id="chapters">
            <h2>Chapters</h2>
            <table>
                <thead>
                    <tr>
                        <th>Chapter</th>
                        <th>Characters</th>
                        <th>Events</th>
                        <th>Relationships</th>
                    </tr>
                </thead>
                <tbody>
                    {chapter_rows}
                </tbody>
            </table>
        </section>
    </main>

    <footer>
        <p>Generated by StoryGraph AI Agent</p>
    </footer>
</body>
</html>"""

    def _render_character_template(
        self,
        profile,
        relationships: list,
        all_characters: dict,
    ) -> str:
        """Render a character page HTML."""
        aliases_html = (
            ", ".join(profile.aliases) if profile.aliases else "No known aliases"
        )
        stars = "★" * int(profile.importance_score * 5) + "☆" * (
            5 - int(profile.importance_score * 5)
        )

        relationships_html = ""
        for rel_history in relationships:
            # Determine the other character
            other_id = (
                rel_history.character_b_id
                if rel_history.character_a_id == profile.id
                else rel_history.character_a_id
            )
            other_name = all_characters.get(other_id)
            other_display = other_name.canonical_name if other_name else other_id

            interactions_html = ""
            for interaction in rel_history.interactions:
                interactions_html += f"""
                <div class="interaction">
                    <p class="interaction-type">{interaction.relation_type}</p>
                    <p><strong>Context:</strong> {interaction.context}</p>
                    <p><strong>Reasoning:</strong> {interaction.reasoning}</p>
                    <div class="quote">
                        "{interaction.evidence.quote}"
                        <p class="attribution">
                            — <a href="chapter-{interaction.evidence.chapter_index:03d}.html">
                                {interaction.evidence.chapter_title}
                            </a>
                        </p>
                    </div>
                </div>
                """

            relationships_html += f"""
            <div class="relationship-history">
                <h3>Relationship with <a href="character-{other_id}.html">{other_display}</a></h3>
                {interactions_html}
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{profile.canonical_name} - Character Profile</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>{profile.canonical_name}</h1>
        <p class="importance-score">{stars}</p>
    </header>

    <nav>
        <a href="index.html">← Back to Index</a>
    </nav>

    <main>
        <section>
            <h2>Profile</h2>
            <p><strong>Also Known As:</strong> <span class="aliases">{aliases_html}</span></p>
            <p><strong>First Appearance:</strong>
                <a href="chapter-{profile.first_appearance_chapter:03d}.html">
                    Chapter {profile.first_appearance_chapter + 1}
                </a>
            </p>
            <p><strong>Description:</strong> {profile.description or "No description available."}</p>
        </section>

        <section>
            <h2>Relationships</h2>
            {relationships_html if relationships_html else "<p>No relationships recorded.</p>"}
        </section>
    </main>

    <footer>
        <p>Generated by StoryGraph AI Agent</p>
    </footer>
</body>
</html>"""

    def _render_chapter_template(
        self,
        chapter,
        events: list,
        relationships: list,
        all_characters: dict,
    ) -> str:
        """Render a chapter page HTML."""
        events_html = ""
        for event in events:
            significance_class = f"significance-{event.significance}"
            involved_names = []
            for char_id in event.involved_characters:
                if char_id in all_characters:
                    name = all_characters[char_id].canonical_name
                    involved_names.append(
                        f'<a href="character-{char_id}.html">{name}</a>'
                    )

            events_html += f"""
            <div class="event-card {significance_class}">
                <p><strong>Significance:</strong> {event.significance.upper()}</p>
                <p>{event.description}</p>
                <p><strong>Involved:</strong> {", ".join(involved_names) or "Unknown"}</p>
                <div class="quote">"{event.evidence_quote}"</div>
            </div>
            """

        relationships_html = ""
        for interaction in relationships:
            char_a_name = all_characters.get(interaction.character_a_id)
            char_b_name = all_characters.get(interaction.character_b_id)
            a_display = char_a_name.canonical_name if char_a_name else "Unknown"
            b_display = char_b_name.canonical_name if char_b_name else "Unknown"

            relationships_html += f"""
            <div class="interaction">
                <p class="interaction-type">{interaction.relation_type}</p>
                <p>
                    <a href="character-{interaction.character_a_id}.html">{a_display}</a>
                    ↔
                    <a href="character-{interaction.character_b_id}.html">{b_display}</a>
                </p>
                <p>{interaction.context}</p>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{chapter.title} - Chapter Analysis</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>{chapter.title}</h1>
        <p class="subtitle">Chapter {chapter.index + 1}</p>
    </header>

    <nav>
        <a href="index.html">← Back to Index</a>
        {f'<a href="chapter-{chapter.index - 1:03d}.html">← Previous Chapter</a>' if chapter.index > 0 else ""}
        <a href="chapter-{chapter.index + 1:03d}.html">Next Chapter →</a>
    </nav>

    <main>
        <section>
            <h2>Summary</h2>
            <p>{chapter.summary or "No summary available."}</p>
        </section>

        <section>
            <h2>Significant Events ({len(events)})</h2>
            {events_html if events_html else "<p>No significant events recorded.</p>"}
        </section>

        <section>
            <h2>Relationship Changes ({len(relationships)})</h2>
            {relationships_html if relationships_html else "<p>No new relationships in this chapter.</p>"}
        </section>
    </main>

    <footer>
        <p>Generated by StoryGraph AI Agent</p>
    </footer>
</body>
</html>"""
