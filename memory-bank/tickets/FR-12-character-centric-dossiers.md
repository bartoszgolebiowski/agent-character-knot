# FR-12: Character-Centric Semantic Dossiers

**Status:** Not Started  
**Priority:** High  
**Epic:** Knowledge Extraction & Core Intelligence  
**Story Points:** 5

---

## Description

To scale relationship analysis to 100+ chapters, the agent must move away from re-reading raw interaction logs. Instead, it must maintain "Character Dossiers" in Semantic Memory. These dossiers represent the refined, accumulated state of a character (identity, traits, goals, and evolution summary).

When analyzing a new chapter, the agent should only be fed the dossiers of characters found in that chapter, ensuring that Chapter 101's context is informed by the "essence" of what happened back in Chapter 3 without increasing token usage linearly.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** Character profiles in Semantic Memory evolve over time, showing a cumulative "Evolution Summary" across chapters.
2. **AC-2:** The LLM receives refined character dossiers instead of raw event histories for characters in the active scene.
3. **AC-3:** Character consistency is maintained over 100+ chapters even when specific early-chapter events have been pruned from episodic memory.
4. **AC-4:** The HTML report surfaces these refined dossiers in the character detail pages.

---

## Technical Description

### Implementation Approach

#### 1. **Model Updates (`src/memory/models.py`)**

Update `CharacterProfile` (or `SemanticMemory`) to include refined fields:

```python
class CharacterProfile(BaseModel):
    identity: str
    core_traits: List[str] = Field(default_factory=list)
    current_goals: List[str] = Field(default_factory=list)
    evolution_summary: str = ""
    last_known_location: Optional[str] = None
```

#### 2. **State Management (`src/memory/state_manager.py`)**

Implement a handler for consolidating chapter extractions into the persistent dossier:

- **Deduplication:** Merge new traits with existing ones.
- **Compression:** Update the evolution summary with a concise note from the current chapter.
- **Pattern:** `new_profile = merge_entity_data(current_profile, chapter_extraction)`

#### 3. **Skill Prompting (`src/prompting/jinja/skills/`)**

Update `analyze_chapter.j2` to accept `relevant_profiles`:

```jinja2
### CHARACTER DOSSIERS
{% for char in relevant_profiles %}
- {{ char.name }}: {{ char.evolution_summary }}
{% endfor %}
```

#### 4. **Coordination Logic**

The `Coordinator` ensures that the dossier is updated after every successful chapter analysis before proceeding to the next chapter.
