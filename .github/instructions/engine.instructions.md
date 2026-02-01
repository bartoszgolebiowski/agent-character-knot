---
applyTo: "src/engine/**/*.py"
---

# Engine Component Instructions

## Guiding Principles

The Engine layer (`src/engine/`) is responsible for orchestration and execution. It acts as the "CPU" of the system.

### Coordinator, Executor, and Agent

- **Coordinator (`coordinator.py`)**: The **State Machine**.
  - **Role**: Pure logic. Decides _what_ to do next using the `TRANSITIONS` table.
  - **Input**: `AgentState`.
  - **Output**: `CoordinatorDecision`.
  - **Rule**: Contains **NO** LLM calls and **NO** side effects.

- **Executor (`executor.py`)**: The **LLM Client Wrapper**.
  - **Role**: Execution. Decides _how_ to call the LLM (Prompt + Model).
  - **Input**: `SkillName`, `context` (dict).
  - **Output**: Structured Pydantic model.
  - **Rule**: Contains **NO** routing logic and **NO** state updates.

- **Agent (`src/agent.py`)**: The **Orchestrator**.
  - **Role**: Loops through state machine decisions, invokes Executor/Tools, and triggers memory updates.

### The Coordinator

The Coordinator implements the system's core routing logic by performing a lookup in the `TRANSITIONS` map.

- **Method**: `next_action(state: AgentState) -> CoordinatorDecision`
- **Logic**: Table-driven lookup based on `WorkflowStage`. Avoid complex if/else trees where possible.
- **Return Values via Decision Factory**:
  - `CoordinatorDecision.llm(...)`
  - `CoordinatorDecision.tool(...)`
  - `CoordinatorDecision.complete(...)`
  - `CoordinatorDecision.noop(...)`

### The Executor

The Executor manages the interaction with the LLM.

1.  **Skill Lookup**: Uses `skill_registry` to find the `SkillDefinition`.
2.  **Prompt Rendering**: Calls `definition.render_prompt(context)`.
3.  **LLM Invocation**: Calls `client.invoke(..., output_model=definition.output_model)`.
4.  **Validation**: The `LLMClient` handles Pydantic validation of the response.

## Common Mistakes to Avoid

- **Don't add LLM calls to the Coordinator.** It must remain a fast, deterministic pure function.
- **Don't put routing logic in the Executor.** The Executor just does what it's told.
- **Don't let the LLM decide the next step.** The Coordinator decides the step; the LLM just performs the task.
- **Don't modify state in the Engine.** State updates happen in `memory/state_manager.py`.
