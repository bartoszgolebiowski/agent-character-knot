# FR-09: Structured Relationship History (Pydantic)

**Status:** Not Started  
**Priority:** High  
**Epic:** State Management  
**Story Points:** 3

---

## Description

All relationship data must be stored using **Pydantic models** with explicit schemas, default values, and field descriptions. This ensures:

1. **Type Safety:** Prevents runtime errors from malformed data
2. **Validation:** Automatic checking that all required fields are present
3. **Documentation:** Field descriptions serve as inline documentation
4. **Serialization:** Easy JSON export for HTML generation and debugging
5. **Compatibility:** Downstream tools (HTML generator, analyzers) can rely on consistent structure

This is a **non-functional requirement** that enforces architectural discipline across the entire codebase. Every piece of relationship data must be a Pydantic model, not a dict or plain Python object.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** All relationship-related data structures are defined as Pydantic `BaseModel` subclasses in `src/memory/models.py` or `src/skills/models.py`.

2. **AC-2:** Every field has:
   - Type annotation (e.g., `str`, `int`, `list[str]`)
   - Description via `Field(description="...")`
   - Default value where applicable

3. **AC-3:** The codebase contains no raw dictionaries for relationship storage (e.g., no `relationship = {"type": "allies", "reason": "..."}`)

4. **AC-4:** Attempting to create a relationship model with missing required fields raises a Pydantic `ValidationError`.

5. **AC-5:** State can be serialized to JSON via `state.model_dump()` and deserialized via `AgentState.model_validate(data)` without errors.

---

## Technical Description

### Implementation Approach

Following the architecture guidelines, all data structures must be Pydantic models.

#### 1. **Core Relationship Models (`src/memory/models.py`)**

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from uuid import uuid4

class RelationshipEvidence(BaseModel):
    """Textual evidence supporting a relationship claim."""
    quote: str = Field(
        description="Verbatim quote from the text (1-3 sentences)",
        min_length=10
    )
    chapter_index: int = Field(
        ge=0,
        description="Zero-based chapter index where quote appears"
    )
    chapter_title: str = Field(
        description="Title of the chapter for human readability"
    )

class RelationshipInteraction(BaseModel):
    """A single relationship entry (moment in time)."""
    interaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this interaction"
    )
    character_a_id: str = Field(
        description="UUID of first character"
    )
    character_b_id: str = Field(
        description="UUID of second character"
    )

    relation_type: str = Field(
        description="Nature of relationship (free-form, e.g., 'Secret Alliance')",
        min_length=3
    )
    reasoning: str = Field(
        description="WHY this relationship exists - logical explanation",
        min_length=10
    )
    context: str = Field(
        description="Brief situation/circumstances of the interaction",
        min_length=10
    )
    evidence: RelationshipEvidence = Field(
        description="Textual proof with chapter reference"
    )

    extracted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when this entry was created"
    )

    # Optional: Cross-chapter causal links (FR-07)
    references_event_id: str | None = Field(
        default=None,
        description="If this interaction references a past event, the event ID"
    )

class RelationshipHistory(BaseModel):
    """Complete history of interactions between two characters."""
    history_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this relationship pair"
    )
    character_a_id: str = Field(
        description="UUID of first character (canonical)"
    )
    character_b_id: str = Field(
        description="UUID of second character (canonical)"
    )
    interactions: list[RelationshipInteraction] = Field(
        default_factory=list,
        description="Chronological list of relationship moments"
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

    class Config:
        frozen = False  # Allow mutations in-place (but always use via deepcopy in handlers)
```

#### 2. **Character Profile Model**

```python
class CharacterProfile(BaseModel):
    """Canonical character entry in the knowledge graph."""
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this character"
    )
    canonical_name: str = Field(
        description="Primary name for this character",
        min_length=1
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="All known names/references for this character"
    )
    first_appearance_chapter: int = Field(
        ge=0,
        description="Chapter index where first mentioned"
    )
    importance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LLM-derived narrative importance (0.0-1.0)"
    )

    # Optional: Character traits (can be extended later)
    traits: list[str] = Field(
        default_factory=list,
        description="Inferred character traits (e.g., 'brave', 'cunning')"
    )
```

#### 3. **Semantic Memory Structure**

```python
class SemanticMemory(BaseModel):
    """Long-term cumulative knowledge graph."""
    characters: dict[str, CharacterProfile] = Field(
        default_factory=dict,
        description="Map of character_id -> profile"
    )
    alias_index: dict[str, str] = Field(
        default_factory=dict,
        description="Map of lowercase alias -> character_id for fast lookup"
    )
    relationships: dict[str, dict[str, RelationshipHistory]] = Field(
        default_factory=dict,
        description="Nested map: character_id -> {other_character_id -> history}"
    )
    event_chronicle: list[SignificantEvent] = Field(
        default_factory=list,
        description="Timeline of major events across all chapters"
    )
```

#### 4. **Validation Examples**

```python
# Valid relationship creation
interaction = RelationshipInteraction(
    character_a_id="uuid-123",
    character_b_id="uuid-456",
    relation_type="Secret Alliance",
    reasoning="They formed a pact to overthrow the king",
    context="Met in a hidden tavern at midnight",
    evidence=RelationshipEvidence(
        quote="We swear to support each other until the tyrant falls.",
        chapter_index=5,
        chapter_title="Chapter 5: The Pact"
    )
)

# Invalid - missing required field (raises ValidationError)
try:
    bad_interaction = RelationshipInteraction(
        character_a_id="uuid-123",
        # Missing character_b_id!
        relation_type="Allies",
        reasoning="Some reason",
        context="Some context",
        evidence=RelationshipEvidence(...)
    )
except ValidationError as e:
    print(e)  # Field required: character_b_id

# Invalid - constraint violation (raises ValidationError)
try:
    bad_evidence = RelationshipEvidence(
        quote="Too short",  # Fails min_length=10
        chapter_index=-1,  # Fails ge=0
        chapter_title="Chapter"
    )
except ValidationError as e:
    print(e)
```

#### 5. **Skill Output Models**

All skill outputs must also be Pydantic models:

```python
# src/skills/models.py

class EntityResolutionOutput(BaseModel):
    """Structured output from entity resolution skill."""
    mappings: list[AliasMapping]
    new_characters: list[str]

class RelationshipExtractionOutput(BaseModel):
    """Structured output from relationship extraction skill."""
    interactions: list[RelationshipInteraction] = Field(
        default_factory=list
    )
    reasoning_summary: str = Field(
        description="Overall narrative summary"
    )
```

#### 6. **State Manager Type Safety**

Handlers must accept and return typed Pydantic models:

```python
# src/memory/state_manager.py

def update_relationship_graph(
    state: AgentState,
    output: RelationshipExtractionOutput  # Typed!
) -> AgentState:
    """Type-safe handler - Pydantic validates output structure."""
    new_state = deepcopy(state)

    for interaction in output.interactions:
        # interaction is guaranteed to have all required fields
        char_a = interaction.character_a_id  # Type-safe access
        char_b = interaction.character_b_id

        # Add to relationship graph
        # ...

    return new_state
```

#### 7. **Serialization/Deserialization**

```python
# Save state to JSON
state_dict = agent_state.model_dump()
with open("state.json", "w") as f:
    json.dump(state_dict, f, indent=2)

# Load state from JSON
with open("state.json", "r") as f:
    state_dict = json.load(f)

validated_state = AgentState.model_validate(state_dict)
# Pydantic automatically validates all nested models
```

### Architecture Compliance

- **All Data is Pydantic:** No raw dicts, tuples, or plain classes
- **Type Annotations:** Every field fully typed
- **Validation:** Constraints enforced (min_length, ge, le, etc.)
- **Default Factories:** Use `Field(default_factory=...)` for mutable defaults
- **Immutability Awareness:** Use `frozen=False` by default, but always mutate via `deepcopy` in handlers
- **Nested Models:** Complex structures (e.g., `RelationshipEvidence`) are their own models

### Testing Strategy

1. **Validation Tests:**
   - Attempt to create models with missing required fields
   - Verify `ValidationError` is raised with correct field names

2. **Serialization Tests:**
   - Create a full `AgentState` with characters, relationships, events
   - Serialize to JSON via `model_dump()`
   - Deserialize via `model_validate()`
   - Verify round-trip equality

3. **Constraint Tests:**
   - Test `min_length` constraints (e.g., empty strings)
   - Test numeric constraints (e.g., negative chapter indices)
   - Test list/dict types (e.g., passing string instead of list)

4. **Type Safety Tests:**
   - Use `mypy` or `pyright` to verify type annotations
   - Run static analysis to catch type mismatches

---

## Dependencies

- Pydantic v2.x
- Python 3.11+ for modern type hints

---

## Questions / Clarifications Needed

- Should we use `frozen=True` on models to enforce immutability at the Pydantic level, or rely on manual `deepcopy`?
- Do we need custom validators for complex constraints (e.g., ensuring `character_a_id != character_b_id`)?
- Should we implement a base model with common fields (e.g., `id`, `created_at`) for all models?
- What should be the minimum/maximum lengths for text fields (`reasoning`, `context`, `quote`)?
- Should we version the models (e.g., `__version__ = "1.0"`) for future schema migrations?
