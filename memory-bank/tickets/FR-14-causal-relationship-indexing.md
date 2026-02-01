# FR-14: Causal Relationship Indexing

**Status:** Not Started  
**Priority:** Medium  
**Epic:** Knowledge Extraction & Core Intelligence  
**Story Points:** 3

---

## Description

The agent must distinguish between "everyday interactions" and "pivotal causal nodes." A relationship change in Chapter 31 might be a direct consequence of a specific event in Chapter 3 (e.g., a debt).

This requirement implements "Active Causal Indexing," where key relationship milestones are tagged as "Active Nodes." These nodes are persisted in the LLM's context window until they are resolved, regardless of how many chapters have passed.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The agent identifies specific past events that directly cause a current relationship change.
2. **AC-2:** Textual evidence (quotes) for the _cause_ is preserved alongside the _effect_.
3. **AC-3:** Causal links are navigable in the HTML report (clicking a "Reason" takes you to the evidence from the past chapter).

---

## Technical Description

### Implementation Approach

#### 1. **Model Updates (`src/memory/models.py`)**

Update `RelationshipInteraction` to include a persistent causality flag:

```python
class RelationshipInteraction(BaseModel):
    # ... existing fields
    is_causal_node: bool = False
    resolved_in_chapter: Optional[int] = None
```

#### 2. **Context Windowing Strategy**

In `Agent._build_prompt_context`:

- Filter relationships to include all interactions from the current rolling window.
- **AND** include all interactions where `is_causal_node=True` and `resolved_in_chapter=None`.

#### 3. **Skill Template Updates**

Update `importance_scoring.j2` or `analyze_chapter.j2` to explicitly ask the LLM to identify if the current interaction resolves a previous "Causal Node" or creates a new one.

#### 4. **HTML Report (`src/tools/html_report_generator.py`)**

Update the relationship timeline to highlight "Causal Nodes" and link them backwards in time to their origin chapters using HTML anchors.
