# Implementation Plan: StoryGraph AI Agent

This document outlines the phased implementation strategy for the StoryGraph AI Agent, adhering strictly to the deterministic, state-driven architecture.

## Phase 1: Foundation & Memory (Infrastructure)

_Fundamental data structures and state management logic._

1.  **[FR-09] Structured Relationship History (Pydantic)**
    - Define all schemas in `src/memory/models.py` and `src/skills/models.py`.
    - Ensure strict typing and field descriptions.
2.  **[FR-08] Incremental Updates (State Manager)**
    - Implement the `StateManager` in `src/memory/state_manager.py`.
    - Create base handlers for skill/tool output ingestion with `deepcopy` logic.
3.  **[FR-03] Sequential Processing (Coordinator)**
    - Define `WorkflowStage` enums in `src/engine/types.py`.
    - Initialize the `TRANSITIONS` table in `src/engine/workflow_transitions.py`.
    - Implement the loop logic in `src/engine/coordinator.py`.

## Phase 2: Data Ingestion (Deterministic Tools)

_Tools to handle high-volume text and structural parsing._

4.  **[FR-02] Intelligent Segmentation**
    - Create `ChapterSegmentationTool` in `src/tools/`.
    - Implement regex-based boundary detection.
5.  **[FR-01] High Volume Support (Chapter Extraction)**
    - Implement `ChapterExtractionTool` to load text lazily (chapter by chapter).
    - Implement progress logging in `src/agent.py`.

## Phase 3: Core Intelligence (LLM Skills)

_AI capabilities for entity and relationship extraction._

6.  **[FR-04] Entity Resolution**
    - Define `entity_resolution.j2` template.
    - Implement the incremental character registry update handler.
7.  **[FR-06] Relationship Attribution**
    - Define `relationship_extraction.j2` template.
    - Implement evidence-based extraction (quotes + reasoning).
    - Update state manager to handle bidirectional graph updates.
8.  **[FR-07] Long-term Reasoning**
    - Implement the `SignificantEvent` chronicle.
    - Create the causal link detection skill and integration logic.
9.  **[FR-05] Importance Scoring**
    - Create the batch scoring skill to run after all chapters are processed.

## Phase 4: Presentation (Reporting)

_Deterministic tools for final output._

10. **[FR-10] & [FR-11] Multi-Page HTML Report & Hyperlinking**
    - Implement `HTMLReportGeneratorTool` using Jinja2.
    - Create templates for Index, Character, and Chapter pages.
    - Implement automatic link generation filters.

## Phase 5: Advanced Scaling (Long-tail Consistency)

_Strategies to handle 100+ chapters._

11. **[FR-12] Character-Centric Semantic Dossiers**
    - Refine `CharacterProfile` in `src/memory/models.py`.
    - Implement the incremental dossier refinement skill and handler.
12. **[FR-13] Hierarchical Memory Consolidation**
    - Implement the consolidation trigger in `coordinator.py`.
    - Create the `consolidate_memory.j2` skill for chapter-to-book summarization.
13. **[FR-14] Causal Relationship Indexing**
    - Add `is_causal_node` flag to `RelationshipInteraction`.
    - Update `_build_prompt_context` in `src/agent.py` to include active causal nodes in the context window.

---

## Critical Rules for Implementation

1.  **State Management**: NEVER mutate `AgentState` directly. Always use `deepcopy` in `state_manager.py`.
2.  **Logic Placement**:
    - Routing logic -> `workflow_transitions.py`.
    - Side effects/Execution -> `agent.py`.
    - LLM Prompting -> `src/prompting/jinja/`.
3.  **Typing**: All new functions must be fully type-hinted using Python 3.11+ syntax.
4.  **Validation**: Use `pydantic.BaseModel` for all data structures to ensure automatic validation.

## Next Steps

1. Start with **Phase 1, Step 1 ([FR-09])**: Defining the Pydantic models in `src/memory/models.py`.
