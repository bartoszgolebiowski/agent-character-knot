# AI Developer Instructions - Agent Research Repo

This project implements a **deterministic, state-driven agent architecture**. You must strictly adhere to the following engineering guidelines.

## 1. Core Architecture Rules

- **State-Driven Flow**: The `Coordinator` (state machine) decides the next action based on `AgentState`. **Never** ask the LLM to decide the control flow.
- **Separation of Concerns**:
  - **Engine**: Logic & Orchestration (`Coordinator`, `Executor`, `Agent`).
  - **Memory**: 7-Layered State Structure (`models.py`) & Updates (`state_manager.py`).
  - **Skills**: Declarative Definitions (`definitions.py`, `templates/*.j2`).
- **Immutability**: Never mutate state in place. Always `deepcopy` before modifying.

## 2. Coding Standards Checklist

### Python & Typing

- Use Python 3.11+ syntax.
- Add `from __future__ import annotations` to every file.
- Use `pydantic.BaseModel` for all data schemas.
- Use `@dataclass(frozen=True, slots=True)` for config/service classes.
- Fully type-hint all functions and methods.
- Use `src/engine/types.py` for shared Enums (`WorkflowStage`, `ActionType`) to avoid circular imports.

### Creating a New Skill

1.  **Define Output Model**: Create a Pydantic model in `skills/models.py`.
2.  **Create Template**: Add a `.j2` file in `src/prompting/jinja/skills/`.
3.  **Register Skill**: Add a `SkillDefinition` in `src/skills/definitions.py`.
4.  **Handle State**: Add a handler function and registry entry in `src/memory/state_manager.py`.
5.  **Add Routing**: Update the `TRANSITIONS` map in `src/engine/workflow_transitions.py`.

### State Management

- **Pattern**: `func(state: AgentState, output: T) -> AgentState`
- **Rule**: `new_state = deepcopy(state)` -> apply changes -> `return new_state`

## 3. Do's and Don'ts

| Category    | DO                                                   | DON'T                                                   |
| :---------- | :--------------------------------------------------- | :------------------------------------------------------ |
| **Prompts** | Use Jinja2 templates in `src/prompting/jinja/`.      | Use f-strings or hardcoded strings in Python.           |
| **Logic**   | Put routing logic in `TRANSITIONS` table.            | Put routing logic in LLM prompts or Skills.             |
| **LLM**     | Use `LLMExecutor` to call `LLMClient`.               | Call `openai` or `requests` directly in business logic. |
| **Config**  | Use `from_env()` factory methods.                    | Hardcode API keys or paths.                             |
| **Imports** | Use absolute imports (e.g., `from ..domain import`). | Use relative imports that break package structure.      |

## 4. File Structure Reference

- `src/engine/workflow_transitions.py`: **State Machine Map** (Edit here to change flow).
- `src/engine/coordinator.py`: **State Machine Logic** (Decides next action via map).
- `src/memory/models.py`: **Data Schemas** (Edit here to change state structure/helpers).
- `src/skills/definitions.py`: **Skill Registry** (Edit here to add capabilities).
- `src/prompting/jinja/`: **Prompt Templates** (Edit here to change LLM instructions).
- `src/llm/`: **LLM Interface** (Client wrapper and configuration).

## 5. Example: Adding a Field to State

```python
# 1. Modify model (src/memory/models.py)
class SemanticMemory(BaseModel):
    new_field: str = "default"

# 2. Update handler (src/memory/state_manager.py)
def update_semantic_memory(state: AgentState, output: NewSkillOutput) -> AgentState:
    new_state = deepcopy(state)
    new_state.semantic.new_field = output.value
    return new_state
```

## Path-Scoped Instructions

For component-specific guidance, see:

- `.github/instructions/architecture.instructions.md` - Overall system
- `.github/instructions/engine.instructions.md` - Agent layer
- `.github/instructions/memory.instructions.md` - Memory system
- `.github/instructions/skills.instructions.md` - Skills layer
- `.github/instructions/templates.instructions.md` - Prompt templates
- `.github/instructions/llm.instructions.md` - LLM Client layer
- `.github/instructions/tools.instructions.md` - Tools layer
