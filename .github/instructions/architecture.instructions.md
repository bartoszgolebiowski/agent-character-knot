---
applyTo: "src/**/*.py"
---

# Architecture Instructions

This document outlines the high-level architectural principles for the Agentic System. The architecture is designed to be modular, state-driven, and easily extensible. It enforces a strict separation of concerns between orchestration, state management, and execution.

## Core Principles

1.  **Separation of Concerns**: The system is divided into distinct layers, each with a single responsibility.
    - **Engine Layer (`src/engine/`)**: Orchestrates the workflow (`Coordinator`, `Agent`) and handles LLM interactions (`Executor`).
    - **State Management Layer (`src/memory/`)**: Manages all data structures (`models.py`) and state transitions (`state_manager.py`).
    - **Capabilities Layer (`src/skills/`)**: Defines the AI's capabilities declaratively (Prompt Templates + Output Schemas).
    - **Tools Layer (`src/tools/`)**: Wrappers for external services (e.g., Search, APIs).
    - **Prompting Layer (`src/prompting/`)**: Manages Jinja2 environments and template loading.
    - **LLM Layer (`src/llm/`)**: Encapsulates LLM client interactions and configurations.

2.  **State-Driven Flow**: The workflow is **not** controlled by the LLM. Instead, a deterministic state machine (`Coordinator`) uses a centralized mapping table (`workflow_transitions.py`) to decide the next action based on `WorkflowStage`.

3.  **Immutable State**: State (`AgentState`) is treated as immutable. Any modification must be done on a **deep copy** of the state object (handled in `state_manager.py`).

4.  **Declarative Capabilities**: AI skills are defined declaratively. They specify _what_ the AI can do (prompt and output structure) but not _how_ to do it (execution logic).

## Request Processing Flow

The system processes tasks through a well-defined, deterministic flow:

1.  **State Analysis**: The `Coordinator` examines the `AgentState`.
2.  **Decision Making**: Based on the `WorkflowStage`, the Coordinator returns a `Decision` (lookup from `TRANSITIONS` map).
3.  **Execution**:
    - If **LLM Skill**: The `Executor` renders the prompt and calls the LLM.
    - If **Tool**: The `Agent` executes the tool client with parameters extracted from `AgentState`.
4.  **State Update**: The result is passed to `state_manager`, which dispatches to a specific handler registry.

## Memory Update Flow

State modifications are handled centrally and explicitly:

1.  **Output Reception**: The `state_manager` receives the output.
2.  **Dedicated Handler**: The output is routed via registry (`_SKILL_HANDLERS` or `_TOOL_HANDLERS`).
3.  **Deep Copy**: The handler creates a `deepcopy` of the current `AgentState`.
4.  **Modification**: The handler updates the copied state and advances fields like `current_stage`.
5.  **Return**: The new state object is returned.

This ensures that all state changes are predictable, traceable, and decoupled from the execution logic.
