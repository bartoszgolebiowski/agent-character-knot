---
applyTo: "src/prompting/**/*.j2"
---

# Templates Component Instructions

## Guiding Principles

The Template system (`prompting/`) handles **context engineering**. It uses Jinja2 to render dynamic prompts based on the current state.

### Directory Structure

Templates are located in `prompting/jinja/`:

- `memory/`: Reusable partials that render specific memory layers (e.g., `core.j2`, `working.j2`).
- `skills/`: Full prompt templates for specific skills (e.g., `skill_name.j2`).

### Template Architecture

1.  **Skill Templates**: The entry point. They define the specific task instructions.
    - Example: "You are an expert. Perform task X..."
2.  **Memory Includes**: Skill templates `{% include %}` memory templates to inject context.
    - Example: `{% include 'memory/core.j2' %}` injects the persona.

### Best Practices

- **Use Jinja2 Logic**: Use `{% if %}` and `{% for %}` to handle optional data and lists.
- **Structured Output Instructions**: explicitly describe the JSON structure expected, even though the LLM client enforces it. It helps the LLM reason.
- **Separation**: Keep the "Persona" in `memory/core.j2` so it's consistent across all skills.
- **Context**: Only include the memory layers relevant to the current skill to save tokens and reduce noise.

## Common Mistakes to Avoid

- **Hardcoding State**: Never write "User name is Bob" in a template. Use `{{ state.semantic.user_name }}`.
- **Complex Logic**: Keep Jinja logic simple (presentation logic only). Business logic belongs in Python.
- **Missing Includes**: Forgetting to include the `core` persona or `working` memory context.
