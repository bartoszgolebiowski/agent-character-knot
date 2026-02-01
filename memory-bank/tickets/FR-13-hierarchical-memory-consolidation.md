# FR-13: Hierarchical Memory Consolidation

**Status:** Not Started  
**Priority:** Medium  
**Epic:** State Management  
**Story Points:** 5

---

## Description

Linear growth of chapter summaries will eventually exceed any LLM context window. This requirement introduces "Hierarchical Consolidation," where the agent periodically compresses groups of chapter summaries into higher-level "Part" or "Book" summaries (e.g., every 10-20 chapters).

This provides the agent with a "telescopic" view of history: high-resolution detail for the last few chapters, and lower-resolution (but still comprehensive) detail for chapters from a long time ago.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The system can handle 300+ chapters (like War and Peace) without the summary list exceeding token limits.
2. **AC-2:** Long-term context is preserved via consolidated summaries.
3. **AC-3:** The HTML report displays both high-level book summaries and detailed chapter summaries.

---

## Technical Description

### Implementation Approach

#### 1. **Model Updates (`src/memory/models.py`)**

Add a storage for consolidated summaries:

```python
class SemanticMemory(BaseModel):
    # ... existing fields
    book_summaries: List[str] = Field(default_factory=list, description="Consolidated summaries of chapter groups")
```

#### 2. **Consolidation Logic (`src/memory/state_manager.py`)**

Implement logic to trigger consolidation:

- **Threshold:** Every 20 chapters.
- **Action:** Send the last 20 `chapter_summaries` to an LLM skill to create one `book_summary`.
- **State Update:** Append the new `book_summary` and clear or archive the 20 `chapter_summaries`.

#### 3. **Workflow Routing (`src/engine/workflow_transitions.py`)**

Add a `CONSOLIDATE_MEMORY` stage to the state machine:

- `WorkflowStage.ANALYZE_CHAPTER` -> (if threshold met) -> `WorkflowStage.CONSOLIDATE_MEMORY` -> `WorkflowStage.CHECK_COMPLETION`.

#### 4. **Skill Template (`src/prompting/jinja/skills/consolidate_memory.j2`)**

Create a prompt that instructs the LLM to summarize a list of chapters into a cohesive narrative arc.
