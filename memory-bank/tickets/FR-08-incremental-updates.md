# FR-08: Incremental Updates

**Status:** Not Started  
**Priority:** High  
**Epic:** State Management  
**Story Points:** 5

---

## Description

The knowledge graph (character registry + relationship network) must be **incrementally updated** after every chapter analysis, not built all at once at the end. This is critical for:

1. **Memory Efficiency:** Avoids holding all raw chapter data in memory simultaneously
2. **Progressive State Building:** Allows each chapter to benefit from knowledge extracted in previous chapters
3. **Natural Flow:** Mirrors how a human reader builds understanding chapter by chapter
4. **Debugging/Monitoring:** Enables inspection of state at any point in the process

The system maintains two distinct memory types:

- **Episodic Memory:** Short-term, chapter-specific data (rolling window)
- **Semantic Memory:** Long-term, cumulative knowledge (character profiles, relationships, event chronicle)

After each chapter:

- Episodic data is extracted and transformed
- Semantic memory is updated (merged, not replaced)
- Episodic data may be pruned to save space

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** After processing Chapter N, the semantic memory contains:
   - All characters discovered in Chapters 1 through N
   - All relationships extracted from Chapters 1 through N
   - All significant events from Chapters 1 through N

2. **AC-2:** When processing Chapter N+1, the LLM has access to:
   - Full semantic memory (cumulative knowledge)
   - Only the text of Chapter N+1 (not all previous chapters)
   - Summaries/events from recent chapters (episodic window)

3. **AC-3:** Memory usage remains stable across the book (doesn't grow unbounded with each chapter).

4. **AC-4:** State can be serialized to JSON after each chapter for:
   - Debugging (inspect intermediate states)
   - Potential future resumability (checkpoint/restore)

5. **AC-5:** The final state is identical whether processing happens in:
   - One continuous run
   - Multiple sessions (with state saved/loaded between chapters)

---

## Technical Description

### Implementation Approach

Following the state-driven architecture, updates flow through the `state_manager` which dispatches to registered handlers.

#### 1. **Memory Structure (`src/memory/models.py`)**

```python
from pydantic import BaseModel, Field
from typing import Any

class EpisodicMemory(BaseModel):
    """Short-term memory - recent chapters and raw extractions."""
    raw_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Unprocessed events from recent chapters"
    )
    recent_chapters: list[int] = Field(
        default_factory=list,
        description="Indices of chapters in the rolling window"
    )
    window_size: int = Field(
        default=5,
        description="Number of recent chapters to retain full details for"
    )

class WorkflowMemory(BaseModel):
    """Workflow state tracking."""
    current_stage: WorkflowStage
    current_chapter_index: int = 0
    total_chapters: int = 0
    completed_stages: list[str] = Field(default_factory=list)

class AgentState(BaseModel):
    """Root state object - immutable, updated via deep copy."""
    working: WorkingMemory = Field(default_factory=WorkingMemory)
    episodic: EpisodicMemory = Field(default_factory=EpisodicMemory)
    semantic: SemanticMemory = Field(default_factory=SemanticMemory)
    workflow: WorkflowMemory

    class Config:
        arbitrary_types_allowed = True
```

#### 2. **State Manager (`src/memory/state_manager.py`)**

```python
from __future__ import annotations
from copy import deepcopy
from src.memory.models import AgentState
from src.skills.base import SkillName
from src.engine.types import ToolName
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

# Type alias for handler functions
StateUpdateHandler = Callable[[AgentState, Any], AgentState]

# Handler registries
_SKILL_HANDLERS: dict[SkillName, StateUpdateHandler] = {}
_TOOL_HANDLERS: dict[ToolName, StateUpdateHandler] = {}


class StateManager:
    """Central dispatcher for all state updates."""

    def ingest_skill_output(
        self,
        state: AgentState,
        skill_name: SkillName,
        output: Any
    ) -> AgentState:
        """
        Route skill output to appropriate handler.

        Pattern:
        1. Lookup handler from registry
        2. Call handler with current state + output
        3. Handler returns new state (via deepcopy)
        4. Return new state to caller
        """
        handler = _SKILL_HANDLERS.get(skill_name)

        if not handler:
            logger.warning(f"No handler registered for skill: {skill_name}")
            return state  # No-op if handler missing

        logger.debug(f"Updating state from {skill_name}")
        return handler(state, output)

    def ingest_tool_output(
        self,
        state: AgentState,
        tool_name: ToolName,
        output: Any
    ) -> AgentState:
        """Route tool output to appropriate handler."""
        handler = _TOOL_HANDLERS.get(tool_name)

        if not handler:
            logger.warning(f"No handler registered for tool: {tool_name}")
            return state

        logger.debug(f"Updating state from {tool_name}")
        return handler(state, output)


# --- Handler Implementations ---

def update_entity_registry(
    state: AgentState,
    output: EntityResolutionOutput
) -> AgentState:
    """Merge new entities into semantic memory."""
    new_state = deepcopy(state)

    # Merge logic (from FR-04)
    for mapping in output.mappings:
        # ... (entity merging code)
        pass

    return new_state


def update_relationship_graph(
    state: AgentState,
    output: RelationshipExtractionOutput
) -> AgentState:
    """Append new interactions to relationship history."""
    new_state = deepcopy(state)

    for interaction in output.interactions:
        # Append to semantic.relationships (from FR-06)
        # ...
        pass

    return new_state


def prune_episodic_memory(state: AgentState) -> AgentState:
    """
    Trim episodic memory to maintain rolling window.
    Called after each chapter completes.
    """
    new_state = deepcopy(state)

    # Keep only last N chapters
    window_size = new_state.episodic.window_size
    if len(new_state.episodic.recent_chapters) > window_size:
        # Remove oldest chapters
        new_state.episodic.recent_chapters = (
            new_state.episodic.recent_chapters[-window_size:]
        )
        # Prune corresponding events (optional - depends on structure)
        # ...

    logger.debug(
        f"Episodic memory pruned to {len(new_state.episodic.recent_chapters)} chapters"
    )

    return new_state


def advance_workflow_stage(
    state: AgentState,
    new_stage: WorkflowStage
) -> AgentState:
    """Move to next workflow stage."""
    new_state = deepcopy(state)
    new_state.workflow.current_stage = new_stage
    new_state.workflow.completed_stages.append(str(new_stage))
    return new_state


# Register handlers
_SKILL_HANDLERS = {
    SkillName.ENTITY_RESOLUTION: update_entity_registry,
    SkillName.RELATIONSHIP_EXTRACTION: update_relationship_graph,
    # ... other skill handlers
}

_TOOL_HANDLERS = {
    ToolName.CHAPTER_SEGMENTATION: lambda s, o: ...,  # From FR-02
    ToolName.CHAPTER_EXTRACTION: lambda s, o: ...,
    # ... other tool handlers
}
```

#### 3. **Chapter Completion Workflow**

After each chapter, the agent performs these incremental updates:

```python
# In src/agent.py

def _complete_chapter(self, state: AgentState) -> AgentState:
    """Finalize processing for current chapter."""

    # 1. Update semantic memory from episodic extractions
    state = self._consolidate_episodic_to_semantic(state)

    # 2. Prune episodic memory (rolling window)
    state = prune_episodic_memory(state)

    # 3. Advance chapter index
    state = self._advance_to_next_chapter(state)

    # 4. Log progress
    logger.info(
        f"Chapter {state.working.current_chapter_index}/{state.working.total_chapters} complete. "
        f"Characters: {len(state.semantic.characters)}, "
        f"Relationships: {sum(len(rels) for rels in state.semantic.relationships.values())}"
    )

    return state
```

#### 4. **State Serialization**

For debugging and potential checkpointing:

```python
# In src/memory/state_manager.py

def save_state(state: AgentState, path: str) -> None:
    """Serialize state to JSON file."""
    import json
    from pathlib import Path

    state_dict = state.model_dump()

    Path(path).write_text(
        json.dumps(state_dict, indent=2, default=str)
    )
    logger.info(f"State saved to {path}")


def load_state(path: str) -> AgentState:
    """Deserialize state from JSON file."""
    import json
    from pathlib import Path

    state_dict = json.loads(Path(path).read_text())
    return AgentState.model_validate(state_dict)
```

#### 5. **Workflow Integration**

In `src/agent.py`:

```python
class Agent:
    def run(self, initial_state: AgentState) -> AgentState:
        state = initial_state

        for iteration in range(MAX_ITERATIONS):
            decision = self.coordinator.next_action(state)

            # Execute action
            if decision.action_type == ActionType.LLM:
                result = self.executor.execute(decision.skill_name, state)
                state = self.state_manager.ingest_skill_output(
                    state, decision.skill_name, result
                )

            # Optional: Save checkpoint after each chapter
            if state.workflow.current_stage == WorkflowStage.CHAPTER_COMPLETE:
                save_state(state, f"checkpoints/chapter_{state.working.current_chapter_index}.json")

            # ...

        return state
```

### Architecture Compliance

- **Immutable State:** All handlers use `deepcopy(state)` before modifications
- **Central Dispatch:** All updates go through `StateManager`
- **Handler Registry:** Skill/Tool outputs mapped to specific handler functions
- **No Side Effects:** Handlers are pure functions (state → state)
- **Type Safety:** Pydantic models validate all state structures

### Testing Strategy

1. **Unit Test - Handler Functions:**
   - Test each handler in isolation with mock inputs
   - Verify original state is not mutated
   - Verify new state has expected changes

2. **Integration Test - Incremental Updates:**
   - Process 3 chapters sequentially
   - After each chapter, verify:
     - New entities appear in semantic memory
     - Relationships are appended (not replaced)
     - Episodic memory is pruned correctly

3. **Serialization Test:**
   - Save state after chapter 5
   - Load state and continue processing
   - Verify final output is identical to continuous run

4. **Memory Leak Test:**
   - Process 100 chapters
   - Monitor memory usage with `memory_profiler`
   - Verify memory plateaus (doesn't grow linearly)

---

## Dependencies

- All FR-04 through FR-07 (entity resolution, relationships, events)
- Pydantic for model serialization

---

## Questions / Clarifications Needed

- Should we implement automatic checkpointing (save every N chapters), or only manual/debug saves?
- What should be the default episodic window size (5 chapters? 10 chapters?)?
- Should we support merging states from parallel runs (e.g., if two users process different halves of a book)?
- Do we need versioning for state schema (to handle future model changes)?
- Should state files be human-readable (JSON) or compressed (pickle/msgpack)?
