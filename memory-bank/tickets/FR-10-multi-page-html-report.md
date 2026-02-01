# FR-10: Multi-Page HTML Report

**Status:** Not Started  
**Priority:** High  
**Epic:** Presentation & Output  
**Story Points:** 8

---

## Description

The system generates a navigable, multi-page HTML report as the final output. This is not a single monolithic page, but a **collection of interconnected HTML files** that form a browsable "book wiki."

The report consists of three main page types:

1. **Character Pages:** Dedicated file for each major character showing:
   - Canonical name + aliases
   - Importance score (visual indicator like star rating)
   - All relationships with interaction histories
   - Cross-references to relevant chapters

2. **Chapter Pages:** Per-chapter pages including:
   - Chapter summary
   - List of significant events extracted
   - Relationship deltas (new/changed relationships introduced in that chapter)
   - Links to involved characters

3. **Index/Landing Page:** Main entry point with:
   - Table of all characters (sorted by importance)
   - Quick links to all chapters
   - Search/filter capabilities (optional for POC)

The entire report uses **Jinja2 templates** for consistent styling and layout. All character names and chapter references are **hyperlinked** for seamless navigation.

This is a **deterministic tool** (not an LLM skill) because it's pure presentation logic transforming structured data into HTML.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The report generator produces:
   - 1 index page (`index.html`)
   - N character pages (one per character, e.g., `character-uuid-123.html`)
   - M chapter pages (one per chapter, e.g., `chapter-05.html`)

2. **AC-2:** All HTML files are:
   - Valid HTML5
   - Styled with CSS (embedded or external stylesheet)
   - Navigable without JavaScript (progressive enhancement)

3. **AC-3:** Character pages display:
   - Header: Canonical name, aliases, importance stars
   - Relationship table with chronological interaction history
   - Each interaction shows: type, reasoning, context, evidence quote, chapter link

4. **AC-4:** Chapter pages display:
   - Chapter title and number
   - Brief summary (if generated)
   - List of events with involved characters (hyperlinked)
   - Relationship changes introduced in this chapter

5. **AC-5:** Index page displays:
   - Searchable/sortable character table
   - Characters sorted by importance score (descending)
   - Links to all chapter pages

6. **AC-6:** All character names and chapter references are hyperlinked:
   - Clicking a character name navigates to their character page
   - Clicking "Chapter 5" navigates to that chapter page

---

## Technical Description

### Implementation Approach

HTML generation is a **Tool** that transforms `AgentState.semantic` into a folder of HTML files.

#### 1. **Tool Structure (`src/tools/html_report_generator.py`)**

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from src.memory.models import AgentState

# Input Model
class HTMLReportRequest(BaseModel):
    """Request to generate HTML report."""
    output_directory: str = Field(
        description="Path where HTML files will be written"
    )
    template_directory: str = Field(
        default="templates/report",
        description="Path to Jinja2 templates"
    )
    report_title: str = Field(
        default="StoryGraph Character Analysis",
        description="Title for the report"
    )
    book_title: str = Field(
        description="Title of the analyzed book"
    )

# Output Model
class HTMLReportResult(BaseModel):
    """Result of HTML report generation."""
    output_path: str = Field(description="Directory where files were written")
    files_generated: list[str] = Field(
        description="List of generated HTML file paths"
    )
    total_characters: int
    total_chapters: int

# Tool Client
@dataclass(frozen=True, slots=True)
class HTMLReportGeneratorTool:
    """Generates multi-page HTML report from semantic memory."""

    def execute(
        self,
        request: HTMLReportRequest,
        state: AgentState
    ) -> HTMLReportResult:
        """
        Generate HTML report files.

        Steps:
        1. Set up Jinja2 environment
        2. Generate index page
        3. Generate character pages (one per character)
        4. Generate chapter pages (one per chapter)
        5. Copy static assets (CSS, images)
        6. Return summary
        """
        output_dir = Path(request.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2
        env = Environment(
            loader=FileSystemLoader(request.template_directory),
            autoescape=True
        )
        env.filters['get_character_name'] = lambda char_id: (
            state.semantic.characters[char_id].canonical_name
        )

        generated_files = []

        # 1. Generate index
        index_path = output_dir / "index.html"
        self._generate_index(env, state, request, index_path)
        generated_files.append(str(index_path))

        # 2. Generate character pages
        for char_id, profile in state.semantic.characters.items():
            char_path = output_dir / f"{char_id}.html"
            self._generate_character_page(env, state, profile, char_path)
            generated_files.append(str(char_path))

        # 3. Generate chapter pages
        for chapter_meta in state.working.chapter_map:
            chapter_path = output_dir / f"chapter-{chapter_meta.index:03d}.html"
            self._generate_chapter_page(env, state, chapter_meta, chapter_path)
            generated_files.append(str(chapter_path))

        # 4. Copy static assets
        self._copy_static_assets(output_dir)

        return HTMLReportResult(
            output_path=str(output_dir),
            files_generated=generated_files,
            total_characters=len(state.semantic.characters),
            total_chapters=len(state.working.chapter_map)
        )

    def _generate_index(self, env, state, request, output_path):
        """Generate index.html with character and chapter lists."""
        # Sort characters by importance
        sorted_chars = sorted(
            state.semantic.characters.values(),
            key=lambda c: c.importance_score,
            reverse=True
        )

        template = env.get_template("index.html.j2")
        html = template.render(
            report_title=request.report_title,
            book_title=request.book_title,
            characters=sorted_chars,
            chapters=state.working.chapter_map
        )

        output_path.write_text(html, encoding="utf-8")

    def _generate_character_page(self, env, state, profile, output_path):
        """Generate individual character page."""
        # Get relationships for this character
        relationships = state.semantic.relationships.get(profile.id, {})

        template = env.get_template("character.html.j2")
        html = template.render(
            character=profile,
            relationships=relationships,
            all_characters=state.semantic.characters
        )

        output_path.write_text(html, encoding="utf-8")

    def _generate_chapter_page(self, env, state, chapter_meta, output_path):
        """Generate individual chapter page."""
        # Find events and relationships from this chapter
        chapter_events = [
            e for e in state.semantic.event_chronicle
            if e.chapter_index == chapter_meta.index
        ]

        # Find relationship interactions from this chapter
        chapter_interactions = []
        for char_rels in state.semantic.relationships.values():
            for history in char_rels.values():
                for interaction in history.interactions:
                    if interaction.evidence.chapter_index == chapter_meta.index:
                        chapter_interactions.append(interaction)

        template = env.get_template("chapter.html.j2")
        html = template.render(
            chapter=chapter_meta,
            events=chapter_events,
            interactions=chapter_interactions,
            all_characters=state.semantic.characters
        )

        output_path.write_text(html, encoding="utf-8")

    def _copy_static_assets(self, output_dir):
        """Copy CSS, images, etc. to output directory."""
        import shutil

        static_dir = Path("templates/report/static")
        if static_dir.exists():
            dest_static = output_dir / "static"
            shutil.copytree(static_dir, dest_static, dirs_exist_ok=True)
```

#### 2. **Jinja2 Templates**

**Index Template (`templates/report/index.html.j2`):**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ report_title }} - {{ book_title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <h1>{{ book_title }}</h1>
        <p class="subtitle">Character Relationship Analysis</p>
    </header>

    <nav>
        <a href="#characters">Characters</a> |
        <a href="#chapters">Chapters</a>
    </nav>

    <main>
        <section id="characters">
            <h2>Characters</h2>
            <table class="character-index">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Importance</th>
                        <th>Aliases</th>
                        <th>First Seen</th>
                    </tr>
                </thead>
                <tbody>
                    {% for char in characters %}
                    <tr>
                        <td>
                            <a href="{{ char.id }}.html">
                                {{ char.canonical_name }}
                            </a>
                        </td>
                        <td>
                            <span class="importance-stars">
                                {{ "★" * (char.importance_score * 5) | int }}
                                {{ "☆" * (5 - (char.importance_score * 5) | int) }}
                            </span>
                        </td>
                        <td>{{ char.aliases | join(", ") }}</td>
                        <td>
                            <a href="chapter-{{ "%03d" | format(char.first_appearance_chapter) }}.html">
                                Chapter {{ char.first_appearance_chapter }}
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>

        <section id="chapters">
            <h2>Chapters</h2>
            <ul class="chapter-list">
                {% for chapter in chapters %}
                <li>
                    <a href="chapter-{{ "%03d" | format(chapter.index) }}.html">
                        {{ chapter.title }}
                    </a>
                    ({{ chapter.line_count }} lines)
                </li>
                {% endfor %}
            </ul>
        </section>
    </main>

    <footer>
        <p>Generated by StoryGraph Agent</p>
    </footer>
</body>
</html>
```

**Character Template (`templates/report/character.html.j2`):**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ character.canonical_name }} - Character Profile</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <nav class="breadcrumb">
        <a href="index.html">← Back to Index</a>
    </nav>

    <header>
        <h1>{{ character.canonical_name }}</h1>
        <p class="aliases"><strong>Also known as:</strong> {{ character.aliases | join(", ") }}</p>
        <p class="importance">
            Importance: {{ "★" * (character.importance_score * 5) | int }}
        </p>
    </header>

    <main>
        <section class="relationships">
            <h2>Relationships</h2>

            {% for other_id, history in relationships.items() %}
            <article class="relationship-card">
                <h3>
                    With <a href="{{ other_id }}.html">
                        {{ all_characters[other_id].canonical_name }}
                    </a>
                </h3>

                <p class="current-status">
                    <strong>Current Status:</strong> {{ history.latest_relation_type }}
                </p>

                <h4>Interaction History</h4>
                <table class="interactions">
                    <thead>
                        <tr>
                            <th>Chapter</th>
                            <th>Relation</th>
                            <th>Context</th>
                            <th>Evidence</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for interaction in history.interactions %}
                        <tr>
                            <td>
                                <a href="chapter-{{ "%03d" | format(interaction.evidence.chapter_index) }}.html">
                                    {{ interaction.evidence.chapter_title }}
                                </a>
                            </td>
                            <td><span class="relation-badge">{{ interaction.relation_type }}</span></td>
                            <td>{{ interaction.context }}</td>
                            <td>
                                <blockquote>"{{ interaction.evidence.quote }}"</blockquote>
                                <details>
                                    <summary>Reasoning</summary>
                                    <p>{{ interaction.reasoning }}</p>
                                </details>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </article>
            {% endfor %}
        </section>
    </main>
</body>
</html>
```

**Chapter Template (`templates/report/chapter.html.j2`):**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>{{ chapter.title }}</title>
    <link rel="stylesheet" href="static/style.css" />
  </head>
  <body>
    <nav class="breadcrumb">
      <a href="index.html">← Back to Index</a>
    </nav>

    <header>
      <h1>{{ chapter.title }}</h1>
      <p>Lines: {{ chapter.start_line }}-{{ chapter.end_line }}</p>
    </header>

    <main>
      <section class="events">
        <h2>Significant Events</h2>
        <ul>
          {% for event in events %}
          <li>
            <p><strong>{{ event.description }}</strong></p>
            <p>
              Involved: {% for char_id in event.involved_characters %}
              <a href="{{ char_id }}.html">
                {{ all_characters[char_id].canonical_name }} </a
              >{% if not loop.last %}, {% endif %} {% endfor %}
            </p>
            <blockquote>"{{ event.evidence_quote }}"</blockquote>
          </li>
          {% endfor %}
        </ul>
      </section>

      <section class="relationships">
        <h2>Relationship Changes</h2>
        <table class="interactions">
          <thead>
            <tr>
              <th>Characters</th>
              <th>Relation</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {% for interaction in interactions %}
            <tr>
              <td>
                <a href="{{ interaction.character_a_id }}.html">
                  {{ all_characters[interaction.character_a_id].canonical_name
                  }}
                </a>
                ↔
                <a href="{{ interaction.character_b_id }}.html">
                  {{ all_characters[interaction.character_b_id].canonical_name
                  }}
                </a>
              </td>
              <td>{{ interaction.relation_type }}</td>
              <td>
                <blockquote>"{{ interaction.evidence.quote }}"</blockquote>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </section>
    </main>
  </body>
</html>
```

#### 3. **CSS Styling (`templates/report/static/style.css`)**

```css
body {
  font-family: "Georgia", serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background: #f5f5f5;
}

header {
  background: #2c3e50;
  color: white;
  padding: 20px;
  border-radius: 8px;
}

.importance-stars {
  color: gold;
  font-size: 1.2em;
}

.relationship-card {
  background: white;
  padding: 20px;
  margin: 20px 0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

blockquote {
  border-left: 4px solid #3498db;
  padding-left: 15px;
  margin: 10px 0;
  font-style: italic;
}

.relation-badge {
  background: #3498db;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em;
}

table {
  width: 100%;
  border-collapse: collapse;
}

table th,
table td {
  padding: 12px;
  border: 1px solid #ddd;
  text-align: left;
}

table th {
  background: #34495e;
  color: white;
}
```

#### 4. **Workflow Integration**

In `src/engine/workflow_transitions.py`:

```python
TRANSITIONS = {
    # After all chapters processed...
    WorkflowStage.ALL_COMPLETE: Decision.tool(ToolName.HTML_REPORT_GENERATION),
    WorkflowStage.REPORT_GENERATED: Decision.complete("Analysis complete"),
}
```

### Architecture Compliance

- **Tool (Not Skill):** Deterministic transformation, no LLM involved
- **Pydantic Models:** Input/output use Pydantic for validation
- **Jinja2 Templates:** All HTML generated from templates (no hardcoded strings)
- **State Access:** Reads from `AgentState.semantic` (immutable)
- **No Side Effects on State:** Only writes files to disk

### Testing Strategy

1. **Unit Test:** Verify each page generation method produces valid HTML
2. **Integration Test:** Generate full report from mock `AgentState` and verify:
   - All expected files created
   - HTML validates (use W3C validator)
   - Links work (internal href targets exist)
3. **Visual Test:** Manual inspection of rendered pages in browser
4. **Accessibility Test:** Check for proper semantic HTML and ARIA labels

---

## Dependencies

- Jinja2 library
- Completed semantic memory (FR-04 through FR-07)

---

## Questions / Clarifications Needed

- Should we include a search feature (JavaScript-based) in the index page?
- Do we need print stylesheets for PDF export?
- Should chapter pages include the full chapter text, or just metadata?
- Do we want dark mode / theme switching?
- Should we generate a TOC (table of contents) sidebar for easier navigation?
