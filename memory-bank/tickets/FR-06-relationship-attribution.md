# FR-06: Relationship Attribution

**Status:** Not Started  
**Priority:** Critical  
**Epic:** Knowledge Extraction & Core Intelligence  
**Story Points:** 13

---

## Description

This is the **core feature** of the StoryGraph Agent. Every detected character relationship must include comprehensive attribution with four required components:

1. **Relation Type:** A free-form string describing the nature of the relationship (e.g., "Secret Alliance", "Father-Son", "Bitter Enemies")
2. **Reasoning:** Logical explanation of **why** this relationship exists (not just "they talked")
3. **Context:** Brief description of the situation/circumstances surrounding the interaction
4. **Evidence:** Direct quote from the source text that supports the claim, plus the chapter number where it appears

This transforms the system from a simple sentiment analyzer into an **evidence-based analytical tool** that provides traceability and prevents hallucinations. Users can click on any relationship and see the exact textual proof.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** Every relationship entry in the knowledge graph contains all four required fields (type, reasoning, context, evidence).

2. **AC-2:** Evidence quotes are:
   - Actual verbatim text from the source (not paraphrased)
   - Between 1-3 sentences long
   - Clearly support the claimed relationship

3. **AC-3:** Chapter numbers in evidence citations are accurate (match the actual source chapter).

4. **AC-4:** Relationship types are descriptive and specific:
   - ✅ "Unrequited Love" (good)
   - ❌ "Positive" (too vague)

5. **AC-5:** The system tracks relationship **evolution** over time:
   - Same character pair can have multiple entries from different chapters
   - Entries are chronologically ordered
   - Example: Chapter 3 (Allies) → Chapter 10 (Betrayal) → Chapter 25 (Reconciliation)

6. **AC-6:** In the HTML report, each relationship displays its full history with all evidence quotes linked to chapter pages.

---

## Technical Description

### Implementation Approach

This is an **LLM Skill** that extracts relationships incrementally from each chapter and appends them to the relationship history in semantic memory.

#### 1. **Output Model (`src/skills/models.py`)**

```python
from pydantic import BaseModel, Field
from datetime import datetime

class RelationshipEvidence(BaseModel):
    """Textual evidence supporting a relationship claim."""
    quote: str = Field(
        description="Verbatim quote from the text (1-3 sentences)"
    )
    chapter_index: int = Field(
        description="Zero-based chapter index where quote appears"
    )
    chapter_title: str = Field(
        description="Title of the chapter for human readability"
    )

class RelationshipInteraction(BaseModel):
    """A single relationship entry (moment in time)."""
    character_a_id: str = Field(description="UUID of first character")
    character_b_id: str = Field(description="UUID of second character")
    
    relation_type: str = Field(
        description="Nature of relationship (free-form, e.g., 'Secret Alliance')"
    )
    reasoning: str = Field(
        description="WHY this relationship exists - logical explanation"
    )
    context: str = Field(
        description="Brief situation/circumstances of the interaction"
    )
    evidence: RelationshipEvidence = Field(
        description="Textual proof with chapter reference"
    )
    
    extracted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp when this entry was created"
    )

class RelationshipExtractionOutput(BaseModel):
    """Result of relationship extraction for a chapter."""
    interactions: list[RelationshipInteraction] = Field(
        default_factory=list,
        description="All relationship moments detected in this chapter"
    )
    reasoning_summary: str = Field(
        description="Overall explanation of relationship dynamics in this chapter"
    )
```

#### 2. **Semantic Memory Structure (`src/memory/models.py`)**

```python
class RelationshipHistory(BaseModel):
    """Complete history of interactions between two characters."""
    character_a_id: str
    character_b_id: str
    interactions: list[RelationshipInteraction] = Field(
        default_factory=list,
        description="Chronological list of relationship moments"
    )
    
    @property
    def latest_relation_type(self) -> str:
        """Get the most recent relationship status."""
        return self.interactions[-1].relation_type if self.interactions else "Unknown"

class SemanticMemory(BaseModel):
    characters: dict[str, CharacterProfile] = Field(default_factory=dict)
    alias_index: dict[str, str] = Field(default_factory=dict)
    
    relationships: dict[str, dict[str, RelationshipHistory]] = Field(
        default_factory=dict,
        description="Nested dict: character_id -> {other_character_id -> history}"
    )
```

#### 3. **Skill Definition (`src/skills/definitions.py`)**

```python
relationship_extraction_skill = SkillDefinition(
    name=SkillName.RELATIONSHIP_EXTRACTION,
    template_path="skills/relationship_extraction.j2",
    output_model=RelationshipExtractionOutput,
)

ALL_SKILLS = [
    # ... other skills
    relationship_extraction_skill,
]
```

#### 4. **Prompt Template (`src/prompting/jinja/skills/relationship_extraction.j2`)**

```jinja
You are analyzing character relationships in a book chapter by chapter.

# Current Chapter
**{{ working.current_chapter_title }}** (Chapter {{ working.current_chapter_index }})

```
{{ working.current_chapter_text[:5000] }}  {# Truncate for token limits #}
```

# Known Characters
{% for char_id, profile in semantic.characters.items() %}
- **{{ profile.canonical_name }}** (ID: {{ char_id }})
  - Aliases: {{ profile.aliases | join(', ') }}
{% endfor %}

# Existing Relationships (for context)
{% for char_id, connections in semantic.relationships.items() %}
{% if connections %}
## {{ semantic.characters[char_id].canonical_name }}
{% for other_id, history in connections.items() %}
  - with **{{ semantic.characters[other_id].canonical_name }}**: {{ history.latest_relation_type }}
{% endfor %}
{% endif %}
{% endfor %}

# Task
Extract all meaningful character interactions from the current chapter. For each interaction:

1. **Identify the Characters:** Use character IDs from the known characters list.
2. **Classify the Relation Type:** Be specific (e.g., "Mentor-Student Bond", "Political Rivalry").
3. **Explain the Reasoning:** WHY is this their relationship? What caused it?
4. **Provide Context:** What situation led to this interaction?
5. **Extract Evidence:** Find a direct quote (1-3 sentences) that proves this relationship exists.

# Critical Rules
- **Evidence MUST be verbatim** - copy exact text, don't paraphrase.
- **Quote MUST support the claim** - don't use unrelated dialogue.
- **Include chapter number** in evidence (chapter_index: {{ working.current_chapter_index }}).
- **Track evolution** - if characters interacted before, note how it changed.
- **Be specific** - "Plotting Revenge" is better than "Negative Relationship".

# Output Format
Provide a JSON object matching the RelationshipExtractionOutput schema.
```

#### 5. **State Update Handler (`src/memory/state_manager.py`)**

```python
def update_relationship_graph(
    state: AgentState,
    output: RelationshipExtractionOutput
) -> AgentState:
    """Append new relationship interactions to the knowledge graph."""
    new_state = deepcopy(state)
    
    for interaction in output.interactions:
        char_a = interaction.character_a_id
        char_b = interaction.character_b_id
        
        # Ensure nested dict structure exists
        if char_a not in new_state.semantic.relationships:
            new_state.semantic.relationships[char_a] = {}
        
        # Get or create relationship history
        if char_b not in new_state.semantic.relationships[char_a]:
            new_state.semantic.relationships[char_a][char_b] = RelationshipHistory(
                character_a_id=char_a,
                character_b_id=char_b,
                interactions=[]
            )
        
        # Append new interaction (chronological order)
        new_state.semantic.relationships[char_a][char_b].interactions.append(
            interaction
        )
        
        # Mirror the relationship (bidirectional graph)
        if char_b not in new_state.semantic.relationships:
            new_state.semantic.relationships[char_b] = {}
        
        if char_a not in new_state.semantic.relationships[char_b]:
            new_state.semantic.relationships[char_b][char_a] = RelationshipHistory(
                character_a_id=char_b,
                character_b_id=char_a,
                interactions=[]
            )
        
        # Add same interaction from B's perspective
        new_state.semantic.relationships[char_b][char_a].interactions.append(
            interaction
        )
    
    return new_state

_SKILL_HANDLERS = {
    SkillName.RELATIONSHIP_EXTRACTION: update_relationship_graph,
    # ... other handlers
}
```

#### 6. **Workflow Integration**

In `src/engine/workflow_transitions.py`:
```python
TRANSITIONS = {
    WorkflowStage.ENTITY_RESOLUTION: Decision.llm(SkillName.RELATIONSHIP_EXTRACTION),
    WorkflowStage.RELATIONSHIP_EXTRACTION: Decision.internal("update_semantic_memory"),
    # ... continue to next chapter
}
```

#### 7. **HTML Report Display**

In character page template (`templates/character.html.j2`):
```html
<h2>Relationships</h2>

{% for other_id, history in character.relationships.items() %}
<div class="relationship-card">
  <h3>With <a href="{{ other_id }}.html">{{ characters[other_id].canonical_name }}</a></h3>
  
  <p><strong>Current Status:</strong> {{ history.latest_relation_type }}</p>
  
  <h4>Interaction History</h4>
  <table>
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
          <a href="chapter-{{ interaction.evidence.chapter_index }}.html">
            {{ interaction.evidence.chapter_title }}
          </a>
        </td>
        <td>{{ interaction.relation_type }}</td>
        <td>{{ interaction.context }}</td>
        <td>
          <blockquote>"{{ interaction.evidence.quote }}"</blockquote>
          <em>Reasoning: {{ interaction.reasoning }}</em>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endfor %}
```

### Architecture Compliance

- **LLM Skill:** Declarative definition with Jinja2 template
- **Structured Output:** Pydantic `RelationshipExtractionOutput` with nested models
- **State Immutability:** Handler uses `deepcopy(state)`
- **Incremental Updates:** Appends to existing relationship history (no overwriting)
- **Bidirectional Graph:** Ensures both characters have the relationship recorded

### Testing Strategy

1. **Unit Test:** Verify `update_relationship_graph` correctly:
   - Creates new relationship histories
   - Appends to existing histories
   - Maintains bidirectional links

2. **Evidence Validation Test:** 
   - Extract relationships from a test chapter
   - Manually verify that quotes are verbatim
   - Check that chapter numbers are correct

3. **Evolution Test:** Process 3 chapters where two characters go from allies to enemies:
   - Verify 2+ entries in relationship history
   - Confirm chronological order
   - Check that latest_relation_type reflects final state

4. **HTML Rendering Test:** Generate character page and verify all interactions display correctly

---

## Dependencies

- `FR-04` (Entity Resolution) - Need character IDs before extracting relationships
- LLM with strong context retention (Claude 3.5 Sonnet or GPT-4)
- HTML template system

---

## Questions / Clarifications Needed

- Should we deduplicate similar interactions within the same chapter (e.g., two quotes showing the same "allies" relationship)?
- How should we handle group interactions (3+ characters)? Create pairwise relationships for all pairs?
- Should reasoning and context be combined into one field, or kept separate?
- What's the maximum acceptable quote length (currently set at "1-3 sentences")?
- Should we support markdown/formatting in evidence quotes (e.g., italics for emphasis)?
