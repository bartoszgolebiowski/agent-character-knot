---
applyTo: "src/memory/**/*.py"
---

# Memory Component Instructions

## Guiding Principles

The Memory layer (`src/memory/`) is the stateful core of the system. It defines the structure of all data and provides the logic for how that data is modified.

### The State

The global state is defined in `models.py` as `AgentState`. It is a composite of seven specialized memory layers:

| Layer              | Model                  | Purpose                                                           |
| :----------------- | :--------------------- | :---------------------------------------------------------------- |
| **Constitutional** | `ConstitutionalMemory` | The "agent's DNA." Security and ethical principles (Guardrails).  |
| **Working**        | `WorkingMemory`        | The context of the current session (RAM). "Right now."            |
| **Workflow**       | `WorkflowMemory`       | _Our Secret Sauce_. The State Machine. Business process location. |
| **Episodic**       | `EpisodicMemory`       | What happened? Interaction history, event logs.                   |
| **Semantic**       | `SemanticMemory`       | What do I know? The knowledge base (RAG), facts.                  |
| **Procedural**     | `ProceduralMemory`     | How do I do it? Tool definitions, APIs, manuals.                  |
| **Resource**       | `ResourceMemory`       | Do I have the resources? System status, API availability, limits. |

### Immutability & Updates

State must be treated as **immutable**.

- **Pattern**: `new_state = deepcopy(old_state)`
- **Location**: All state mutation logic resides in `state_manager.py`.
- **Registry Pattern**: Handlers are registered in `_SKILL_HANDLERS` and `_TOOL_HANDLERS` for clean dispatching.

### Logic in Models

While `models.py` primarily defines structure, `AgentState` is permitted to have helper methods for "Data Transformation" (e.g., `get_tool_request_payload`). These methods should only extract and format data for external components (like tools) and never perform side effects or complex business logic.

### Structured Data Models

All data structures must be Pydantic `BaseModel`s.

- **Type Safety**: Use shared Enums from `src/engine/types.py` (e.g., `WorkflowStage`).
- **Initialization**: `create_initial_state` ensures all memory layers are instantiated correctly.

## State Management Logic

### Update Handlers

Handlers should follow this sequence:

1.  **Deepcopy**: `new_state = deepcopy(state)`.
2.  **Mapping**: Extract data from `output` and store in `new_state`.
3.  **Progression**: Advance `new_state.workflow.current_stage` to the next logical stage.
4.  **Registry**: Register new handlers in the file's internal handler maps.

## Common Mistakes to Avoid

- **Don't mutate `state` in place.** Always `deepcopy`.
- **Don't put logic in `models.py`.** Models are for data definition only.
- **Don't mix layers.** Workflow flags go in `WorkflowState`, not `SemanticMemory`.
- **Don't forget `from __future__ import annotations`.**
