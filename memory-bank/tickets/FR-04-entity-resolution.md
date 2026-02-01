# FR-04: Entity Resolution

**Status:** Not Started  
**Priority:** Critical  
**Epic:** Knowledge Extraction & Core Intelligence  
**Story Points:** 8

---

## Description

The system must accurately identify characters and merge various aliases/references to the same person into a single canonical entity. This is one of the most challenging aspects of the project because:

- Characters are referred to differently throughout the book (Jon Snow = Jon = Lord Commander = The Bastard of Winterfell)
- Nicknames, titles, and pronouns must be resolved to avoid duplicate profiles
- Merging happens **incrementally per chapter** as new mentions appear
- The system must avoid false positives (merging two different characters named "John")

Without accurate entity resolution, the relationship graph becomes unusable - you'd have separate nodes for "Gandalf" and "Mithrandir" instead of recognizing they're the same wizard.

This is an **LLM Skill** because it requires:
- Contextual understanding (not just string matching)
- Reasoning about character traits and roles
- Handling ambiguous references

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The system maintains a canonical character registry where each character has:
   - One primary/canonical name
   - A list of known aliases
   - A unique identifier (e.g., UUID or slug)

2. **AC-2:** When a new mention is detected, the system:
   - Checks if it's an alias of an existing character
   - If yes, adds the alias to the existing profile
   - If no, creates a new character entry

3. **AC-3:** Alias resolution accuracy is ≥90% for major characters (tested against manually annotated ground truth for a sample book).

4. **AC-4:** The system avoids false positives (doesn't merge "King Robert" with "Robert the Squire" if they're different people).

5. **AC-5:** The final HTML report shows character pages with:
   - Primary name as the page title
   - "Also known as: [alias1], [alias2], ..." section

---

## Technical Description

### Implementation Approach

Following the Skills layer guidelines, entity resolution is implemented as an LLM Skill with structured output.

#### 1. **Output Model (`src/skills/models.py`)**

```python
from pydantic import BaseModel, Field
from typing import Literal

class MentionedCharacter(BaseModel):
    """A character mentioned in the current chapter."""
    name: str = Field(description="Name or reference as it appears in text")
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence that this is a real character (not a background extra)"
    )

class AliasMapping(BaseModel):
    """Maps a new alias to an existing canonical character."""
    alias: str = Field(description="The new mention/name found in text")
    canonical_id: str | None = Field(
        description="UUID of existing character, or null if new character"
    )
    reasoning: str = Field(
        description="Why this alias belongs to this character (or why it's new)"
    )

class EntityResolutionOutput(BaseModel):
    """Result of entity resolution for a chapter."""
    mappings: list[AliasMapping] = Field(
        description="List of alias-to-canonical mappings"
    )
    new_characters: list[str] = Field(
        description="Names that represent entirely new characters"
    )
```

#### 2. **Semantic Memory Structure (`src/memory/models.py`)**

```python
from uuid import uuid4

class CharacterProfile(BaseModel):
    """Canonical character entry in the knowledge graph."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_name: str = Field(description="Primary name for this character")
    aliases: list[str] = Field(
        default_factory=list,
        description="All known names/references for this character"
    )
    first_appearance_chapter: int = Field(
        description="Chapter index where first mentioned"
    )
    importance_score: float = Field(
        default=0.0,
        description="LLM-derived score (for sorting, not filtering)"
    )

class SemanticMemory(BaseModel):
    characters: dict[str, CharacterProfile] = Field(
        default_factory=dict,
        description="Map of character_id -> profile"
    )
    alias_index: dict[str, str] = Field(
        default_factory=dict,
        description="Map of alias -> character_id for fast lookup"
    )
```

#### 3. **Skill Definition (`src/skills/definitions.py`)**

```python
from src.skills.base import SkillName, SkillDefinition
from src.skills.models import EntityResolutionOutput

entity_resolution_skill = SkillDefinition(
    name=SkillName.ENTITY_RESOLUTION,
    template_path="skills/entity_resolution.j2",
    output_model=EntityResolutionOutput,
)

ALL_SKILLS = [
    entity_resolution_skill,
    # ... other skills
]
```

#### 4. **Prompt Template (`src/prompting/jinja/skills/entity_resolution.j2`)**

```jinja
You are analyzing a book chapter by chapter to build a character registry.

# Current Chapter
{{ working.current_chapter_title }}

```
{{ working.current_chapter_text[:3000] }}  {# Truncate for context limits #}
```

# Existing Character Registry
{% if semantic.characters %}
{% for char_id, profile in semantic.characters.items() %}
- **{{ profile.canonical_name }}** (ID: {{ char_id }})
  - Aliases: {{ profile.aliases | join(', ') }}
  - First seen: Chapter {{ profile.first_appearance_chapter }}
{% endfor %}
{% else %}
No characters registered yet.
{% endif %}

# Task
1. Extract all character names mentioned in the current chapter.
2. For each mention, determine if it's:
   - A new alias for an existing character (provide character ID)
   - An entirely new character (provide null for canonical_id)

3. Provide reasoning for each mapping.

# Rules
- Be conservative: Only merge if you're confident it's the same person.
- Consider context clues (titles, relationships, actions).
- If unsure, treat as a new character (can merge later).

# Output Format
Provide a JSON object matching the EntityResolutionOutput schema.
```

#### 5. **State Update Handler (`src/memory/state_manager.py`)**

```python
def update_entity_registry(
    state: AgentState,
    output: EntityResolutionOutput
) -> AgentState:
    """Merge new aliases into character registry."""
    new_state = deepcopy(state)
    current_chapter = new_state.working.current_chapter_index
    
    for mapping in output.mappings:
        if mapping.canonical_id:
            # Add alias to existing character
            char = new_state.semantic.characters[mapping.canonical_id]
            if mapping.alias not in char.aliases:
                char.aliases.append(mapping.alias)
                new_state.semantic.alias_index[mapping.alias.lower()] = mapping.canonical_id
        else:
            # Create new character
            new_char = CharacterProfile(
                canonical_name=mapping.alias,
                aliases=[mapping.alias],
                first_appearance_chapter=current_chapter,
            )
            new_state.semantic.characters[new_char.id] = new_char
            new_state.semantic.alias_index[mapping.alias.lower()] = new_char.id
    
    return new_state

# Register handler
_SKILL_HANDLERS = {
    SkillName.ENTITY_RESOLUTION: update_entity_registry,
    # ... other handlers
}
```

#### 6. **Workflow Integration**

In `src/engine/workflow_transitions.py`:
```python
TRANSITIONS = {
    WorkflowStage.LOAD_CHAPTER: Decision.llm(SkillName.ENTITY_RESOLUTION),
    WorkflowStage.ENTITY_RESOLUTION: Decision.llm(SkillName.RELATIONSHIP_EXTRACTION),
    # ... continue workflow
}
```

### Advanced: Multi-Pass Resolution

For higher accuracy, implement a two-stage approach:

**Pass 1 (per chapter):** Quick extraction with conservative merging  
**Pass 2 (end of book):** Global resolution pass that reviews all aliases and suggests additional merges

This requires an additional skill:
```python
class GlobalEntityReviewOutput(BaseModel):
    """Suggested merges after full book analysis."""
    merge_suggestions: list[tuple[str, str]] = Field(
        description="Pairs of character IDs that should be merged"
    )
```

### Architecture Compliance

- **LLM Skill:** Uses `SkillDefinition` with Jinja2 template
- **Structured Output:** Pydantic `EntityResolutionOutput` model
- **State Update:** Via `state_manager` handler with `deepcopy`
- **No Logic in Template:** Prompt focuses on extraction, not flow control
- **Memory Included:** Template uses `{% include 'memory/semantic.j2' %}` for character context

### Testing Strategy

1. **Unit Test:** Mock `EntityResolutionOutput` and verify `update_entity_registry` correctly updates state
2. **Integration Test:** Process a test chapter with known aliases (e.g., "Gandalf" and "Mithrandir" appearing in the same chapter)
3. **Accuracy Test:** Annotate a sample book with ground truth aliases and measure precision/recall

---

## Dependencies

- `src/prompting/jinja/memory/semantic.j2` - Template partial for character registry
- LLM with strong reasoning (GPT-4 or Claude 3.5 Sonnet)

---

## Questions / Clarifications Needed

- Should we support manual corrections (user can override incorrect merges via a config file)?
- What's the priority: avoiding false positives (wrong merges) vs. avoiding false negatives (missed merges)?
- Should nicknames be stored separately from formal names in the alias list, or mixed together?
- Do we need to track gendered pronouns (he/she) as part of entity disambiguation?
