# FR-01: High Volume Support

**Status:** Not Started  
**Priority:** High  
**Epic:** Data Ingestion & Processing  
**Story Points:** 5

---

## Description

The StoryGraph AI Agent must be capable of processing large-scale literary works containing up to 100,000 lines of text without memory crashes, performance degradation, or data loss. This is essential for analyzing epic sagas, multi-volume series, and complex narratives like "War and Peace" or "The Lord of the Rings."

The system needs to handle:
- Large text files (potentially 5-10 MB or more)
- Sequential chapter-by-chapter processing without memory leaks
- Stable state management across hundreds of incremental updates
- Efficient context windowing to stay within LLM token limits

This capability is foundational to the product's value proposition - without it, users cannot analyze the very books they care about most.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The system successfully processes a complete text file containing 100,000 lines without crashing or running out of memory.
2. **AC-2:** Processing completes successfully for standard literary works (e.g., War and Peace, ~66k lines).
3. **AC-3:** The system provides progress updates (e.g., "Processing Chapter 5/40") so users can monitor long-running operations.
4. **AC-4:** All character relationships and events from the final chapters are captured with the same fidelity as those from the first chapters (no degradation over time).
5. **AC-5:** The final HTML report is generated successfully even after processing the maximum supported volume.

---

## Technical Description

### Implementation Approach

Following the state-driven architecture:

#### 1. **State Management (`src/memory/models.py`)**

- **AgentState.working.current_chapter_index**: Track progress through the book.
- **AgentState.working.total_chapters**: Total chapter count for progress reporting.
- **AgentState.episodic**: Design to store only recent chapters (e.g., last 5-10) using a rolling window.
- **AgentState.semantic**: Contains cumulative knowledge that grows incrementally but in a structured, deduplicated manner.

**Pattern:**
```python
class WorkingMemory(BaseModel):
    current_chapter_index: int = 0
    total_chapters: int = 0
    current_chapter_text: str = ""
    current_chapter_title: str = ""
```

#### 2. **Chunking Strategy (Tool Layer)**

Create a `ChapterSegmentationTool` in `src/tools/`:
- **Input:** Full text file path
- **Output:** `ChapterMetadata` (list of chapter boundaries with start/end line numbers)
- **Logic:** Regex pattern matching for chapter markers (e.g., "CHAPTER", "PART", "BOOK")

Create a `ChapterExtractionTool`:
- **Input:** File path + chapter index
- **Output:** `ChapterText` (just the text for that specific chapter)
- **Memory Efficiency:** Only loads one chapter into memory at a time

#### 3. **State Updates (Memory Manager)**

In `src/memory/state_manager.py`:
```python
def update_chapter_progress(state: AgentState, chapter_index: int, total: int) -> AgentState:
    new_state = deepcopy(state)
    new_state.working.current_chapter_index = chapter_index
    new_state.working.total_chapters = total
    return new_state
```

#### 4. **Workflow Transitions**

In `src/engine/workflow_transitions.py`:
```python
TRANSITIONS = {
    WorkflowStage.SEGMENTATION: Decision.tool(ToolName.CHAPTER_SEGMENTATION),
    WorkflowStage.LOAD_CHAPTER: Decision.tool(ToolName.CHAPTER_EXTRACTION),
    WorkflowStage.ANALYZE_CHAPTER: Decision.llm(SkillName.ANALYZE_CHAPTER),
    # ... loop back to LOAD_CHAPTER until all chapters processed
}
```

#### 5. **Progress Reporting**

In the main agent loop (`src/agent.py`):
- After each chapter completes, log: `f"Processing Chapter {current}/{total}"`
- Use Python's `logging` module (already configured in `src/logger.py`)

#### 6. **Memory Optimization**

- **Episodic Memory Pruning:** Keep only the last N chapters in `episodic.raw_events`.
- **Context Summarization:** After each chapter, optionally run a "summarize chapter" skill that condenses the chapter into key bullet points for long-term reference.
- **Semantic Deduplication:** When updating character profiles, merge aliases aggressively to avoid storing redundant entities.

### Architecture Compliance

- **Coordinator (`src/engine/coordinator.py`):** Decides to loop through chapters based on `current_chapter_index < total_chapters`.
- **Tools (`src/tools/`):** Handle file I/O and chapter extraction (deterministic, no LLM).
- **State Manager:** All progress updates go through `state_manager.py` handlers.
- **No Direct Mutation:** Always use `deepcopy(state)` before modifying.

### Testing Strategy

1. Create a test fixture with a 100k line text file (concatenate War and Peace multiple times if needed).
2. Run the full pipeline and monitor memory usage (use `memory_profiler`).
3. Verify final state contains data from both chapter 1 and the final chapter.
4. Check that HTML report generation completes without errors.

---

## Dependencies

- Python `memory_profiler` for testing
- Efficient Pydantic model serialization (use `model_dump()` instead of keeping full objects in memory)

---

## Questions / Clarifications Needed

- What is the maximum acceptable processing time for 100k lines? (e.g., 30 minutes? 2 hours?)
- Should we implement checkpointing (save state to disk after every N chapters) for crash recovery?
- Do we need to support incremental/resumable processing, or is single-run processing acceptable for POC?
