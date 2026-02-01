---
applyTo: "src/llm/**/*.py"
---

# LLM Component Instructions

## Guiding Principles

The LLM layer (`llm/`) provides a unified, type-safe interface for interacting with Large Language Models. It abstracts away the specific provider details (OpenAI, OpenRouter, etc.) and enforces structured output validation.

### Core Responsibilities

1.  **Configuration**: Managing API keys, model selection, and parameters via `LLMConfig`.
2.  **Client Abstraction**: Wrapping the underlying SDK (e.g., `openai`) in a `LLMClient` class.
3.  **Structured Output**: Ensuring all LLM calls return validated Pydantic models, not raw strings.
4.  **Error Handling**: converting provider-specific errors into domain-specific exceptions (`LLMCallError`).

## Architecture

### The LLM Client

The `LLMClient` is the only component that should import or use the external LLM SDK.

- **Input**: A prompt string and a Pydantic `output_model` class.
- **Output**: An instance of the `output_model`.
- **Method**: `invoke(prompt: str, output_model: Type[T]) -> T`

### Configuration

Configuration should be immutable and loaded from environment variables.

- Use `LLMConfig.from_env()` to load settings.
- Support standard variables like `API_KEY`, `MODEL`, `TEMPERATURE`.

## Best Practices

- **Structured Output Only**: Do not add methods that return raw strings. The entire architecture relies on structured data.
- **Type Safety**: Use Generics (`TypeVar`) to ensure the `invoke` method returns the correct type based on the `output_model` argument.
- **Error Wrapping**: Catch `openai.APIError` (and others) and raise `LLMCallError` to decouple the upper layers from the specific provider.

## Common Mistakes to Avoid

- **Don't put business logic in the LLM Client.** It should just send the prompt and parse the result.
- **Don't hardcode models or keys.** Always use the `LLMConfig` class.
- **Don't return `Dict`.** Always return Pydantic models.
