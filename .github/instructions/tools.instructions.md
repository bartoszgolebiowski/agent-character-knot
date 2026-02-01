---
applyTo: "src/tools/**/*.py"
---

# Tools Component Instructions

## Guiding Principles

The Tools layer (`tools/`) provides interfaces to external services (e.g., Web Search, APIs).

### What is a Tool?

A Tool is a Python class that wraps an external API or local function.

- **Wrapper Class**: e.g., `ExampleToolClient`.
- **Input Model**: A Pydantic model defining the parameters (e.g., `ExampleToolRequest`).
- **Output Model**: A Pydantic model defining the result (e.g., `ToolResult`).

### Integration with Engine

Tools are triggered by the `Coordinator`:

1.  **Decision**: Coordinator returns `Decision.tool(ToolName.EXAMPLE_TOOL, ...)`.
2.  **Execution**: The main loop (or a ToolExecutor) calls the tool's method.
3.  **State Update**: The tool's output is passed to `state_manager.ingest_tool_results` (or similar).

## Creating New Tools

1.  **Define Models**: Create Input/Output Pydantic models in `tools/models.py`.
2.  **Implement Client**: Create a wrapper class in `tools/<tool_name>.py`.
    - Should accept configuration (API keys) via `__init__`.
    - Should have a main execution method (e.g., `search`, `execute`).
    - Should return the normalized Output Model.
3.  **Register Name**: Add to `ToolName` enum in `domain.py`.
4.  **Add Routing**: Update `Coordinator` to decide when to use this tool.
5.  **Handle Output**: Add a handler in `state_manager.py` to ingest the tool's result into the state.

## Common Mistakes to Avoid

- **Don't put business logic in tools.** Tools should just execute the request and return data.
- **Don't return raw API responses.** Always normalize to a Pydantic model (`ToolResult`) to decouple the rest of the system from the specific API provider.
- **Don't access global state in tools.** Pass all necessary parameters as arguments.
