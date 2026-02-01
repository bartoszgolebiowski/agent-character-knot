# FR-05: Importance Score (No Filtering in POC)

**Status:** Not Started  
**Priority:** Medium  
**Epic:** Knowledge Extraction & Core Intelligence  
**Story Points:** 2

---

## Description

The system computes an LLM-derived "importance score" for each character to enable better UX through sorting and prioritization in the HTML report. However, **the POC must not filter out characters based on this score** - all detected characters must appear in the final output.

The importance score helps readers by:
- Showing major characters at the top of index pages
- Providing context about character significance
- Enabling future features (e.g., "show only main characters" toggle in UI)

This is an **LLM Skill** because importance is subjective and context-dependent (number of mentions alone isn't enough - a character who appears once but causes a major plot event is more important than a servant mentioned 10 times).

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** Every character in the final registry has an `importance_score` field (float, 0.0-1.0).
2. **AC-2:** The HTML index page lists characters sorted by importance score (descending).
3. **AC-3:** No character is excluded from the report based on importance score.
4. **AC-4:** The score roughly correlates with narrative significance:
   - Main protagonist: ~0.9-1.0
   - Major supporting characters: ~0.6-0.8
   - Minor but named characters: ~0.3-0.5
   - Background characters: ~0.1-0.2

5. **AC-5:** The scoring logic is documented so users understand what makes a character "important."

---

## Technical Description

### Implementation Approach

Importance scoring can happen either:
- **Incrementally:** Update score after each chapter based on that chapter's interactions
- **Batch:** Compute all scores at the end after full book analysis

For simplicity and accuracy, we'll use the **batch approach** (final scoring after all chapters are processed).

#### 1. **Output Model (`src/skills/models.py`)**

```python
from pydantic import BaseModel, Field

class CharacterImportanceScore(BaseModel):
    """Importance assessment for a single character."""
    character_id: str = Field(description="UUID of the character")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 (background) to 1.0 (protagonist)"
    )
    reasoning: str = Field(
        description="Brief explanation of why this score was assigned"
    )

class ImportanceScoringOutput(BaseModel):
    """Result of importance scoring for all characters."""
    scores: list[CharacterImportanceScore] = Field(
        description="Importance scores for all characters"
    )
```

#### 2. **Skill Definition (`src/skills/definitions.py`)**

```python
importance_scoring_skill = SkillDefinition(
    name=SkillName.IMPORTANCE_SCORING,
    template_path="skills/importance_scoring.j2",
    output_model=ImportanceScoringOutput,
)

ALL_SKILLS = [
    # ... other skills
    importance_scoring_skill,
]
```

#### 3. **Prompt Template (`src/prompting/jinja/skills/importance_scoring.j2`)**

```jinja
You are assessing the narrative importance of characters in a book.

# Character Registry
{% for char_id, profile in semantic.characters.items() %}
## {{ profile.canonical_name }}
- **ID:** {{ char_id }}
- **Aliases:** {{ profile.aliases | join(', ') }}
- **First Appearance:** Chapter {{ profile.first_appearance_chapter }}
- **Relationship Count:** {{ semantic.relationships[char_id] | length if char_id in semantic.relationships else 0 }}
{% endfor %}

# Relationship Summary
{% for char_id, relationships in semantic.relationships.items() %}
- **{{ semantic.characters[char_id].canonical_name }}:** {{ relationships | length }} connections
{% endfor %}

# Task
Assign each character an importance score from 0.0 to 1.0 based on:

1. **Narrative Centrality:** Do they drive the plot or just observe?
2. **Interaction Depth:** Quality of relationships (not just quantity)
3. **Appearance Frequency:** Chapters in which they're mentioned
4. **Story Impact:** Do they cause major events or just react?

# Scoring Guidelines
- **1.0:** Main protagonist(s) - the story is about them
- **0.7-0.9:** Major supporting characters - essential to main plot
- **0.4-0.6:** Recurring characters - meaningful but not central
- **0.2-0.3:** Named minor characters - appear briefly
- **0.0-0.1:** Background mentions - barely relevant

# Output Format
Provide a JSON object matching the ImportanceScoringOutput schema.
Include brief reasoning for each score.
```

#### 4. **State Update (`src/memory/state_manager.py`)**

```python
def update_importance_scores(
    state: AgentState,
    output: ImportanceScoringOutput
) -> AgentState:
    """Apply importance scores to character profiles."""
    new_state = deepcopy(state)
    
    for score_entry in output.scores:
        char_id = score_entry.character_id
        if char_id in new_state.semantic.characters:
            new_state.semantic.characters[char_id].importance_score = score_entry.score
        else:
            # Log warning if character not found
            logger.warning(f"Character ID {char_id} not found in registry")
    
    return new_state

_SKILL_HANDLERS = {
    SkillName.IMPORTANCE_SCORING: update_importance_scores,
    # ... other handlers
}
```

#### 5. **Workflow Integration**

In `src/engine/workflow_transitions.py`:
```python
TRANSITIONS = {
    # ... earlier stages
    WorkflowStage.ALL_CHAPTERS_COMPLETE: Decision.llm(SkillName.IMPORTANCE_SCORING),
    WorkflowStage.SCORING_COMPLETE: Decision.tool(ToolName.HTML_REPORT_GENERATION),
    # ...
}
```

#### 6. **HTML Report Integration**

In the HTML generation tool (`src/tools/html_report_generation.py`):
```python
def generate_character_index(characters: dict[str, CharacterProfile]) -> str:
    """Generate index.html with characters sorted by importance."""
    
    # Sort characters by importance score (descending)
    sorted_chars = sorted(
        characters.values(),
        key=lambda c: c.importance_score,
        reverse=True
    )
    
    # Render template
    return jinja_env.get_template("index.html.j2").render(
        characters=sorted_chars
    )
```

In the Jinja template (`templates/index.html.j2`):
```html
<h1>Character Index</h1>
<p>Characters sorted by narrative importance</p>

<table>
  <thead>
    <tr>
      <th>Character</th>
      <th>Importance</th>
      <th>First Appearance</th>
    </tr>
  </thead>
  <tbody>
    {% for char in characters %}
    <tr>
      <td><a href="{{ char.id }}.html">{{ char.canonical_name }}</a></td>
      <td>{{ "★" * (char.importance_score * 5) | int }}</td>
      <td>Chapter {{ char.first_appearance_chapter }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

### Alternative: Incremental Scoring

For large books, you may want to compute scores incrementally to avoid token limits. In this case:

1. Each chapter analysis includes a "significance" field for mentioned characters
2. Importance score = average significance across all chapters
3. Final pass normalizes scores to 0.0-1.0 range

#### 7. **Preventing Filtering (Critical for POC)**

Ensure no code path filters characters based on score:
```python
# WRONG - Do not do this
characters_to_display = [c for c in characters if c.importance_score > 0.3]

# CORRECT - Display all characters
characters_to_display = list(characters.values())
```

Add a test to verify all extracted characters appear in the HTML report.

### Architecture Compliance

- **LLM Skill:** Uses `SkillDefinition` with structured output
- **Batch Processing:** Runs once after all chapters analyzed
- **State Update:** Via `state_manager` handler
- **No Filtering:** Score used only for sorting in presentation layer
- **Pydantic Model:** `ImportanceScoringOutput` with validation

### Testing Strategy

1. **Unit Test:** Verify `update_importance_scores` correctly applies scores to profiles
2. **Integration Test:** Process a sample book and verify:
   - All characters have scores
   - Protagonist has highest score
   - Background characters have low scores
3. **UI Test:** Check HTML index shows characters in correct order
4. **Regression Test:** Ensure no characters are missing from final report

---

## Dependencies

- `FR-04` (Entity Resolution) must be complete to have character registry
- `FR-06` (Relationship Attribution) may influence scoring (more relationships = higher importance)

---

## Questions / Clarifications Needed

- Should the scoring prompt include chapter summaries, or just relationship data?
- Do we want to expose the importance score visually in the report (e.g., star ratings), or keep it hidden for sorting only?
- Should there be a minimum number of mentions required before scoring, or score all characters including one-time mentions?
- Can users override scores manually via configuration?
