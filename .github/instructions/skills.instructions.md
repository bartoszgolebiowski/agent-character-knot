---
applyTo: "src/skills/**/*.py"
---

# Skills Component Instructions

## Guiding Principles

The Skills layer (`skills/`) contains the **declarative definitions** of the AI's capabilities.

### What is a Skill?

A Skill is defined by the `SkillDefinition` class (`definitions.py`) and consists of:

1.  **Name**: A unique `SkillName` enum value.
2.  **Prompt Template**: A Jinja2 template path (e.g., `skills/skill_name.j2`).
3.  **Output Model**: A Pydantic model class defining the expected structure (e.g., `SkillOutput`).

### Core Rule: No Execution Logic

- Skills are **data**, not code.
- They do **not** have `.execute()` methods.
- They do **not** call APIs.
- They simply define: "If you want to do X, ask the LLM _this_ and expect _that_ back."

## Creating New Skills

To add a new capability:

1.  **Define Output Model**: Create a Pydantic model in `src/skills/models.py`.
    - Focus on the data required by the `state_manager` to advance the workflow.
    - Fields should be well-documented using Pydantic `Field`.
2.  **Create Template**: Add a `.j2` file in `src/prompting/jinja/skills/`.
    - Use `{% include %}` for memory partials.
3.  **Register Skill**:
    - Add the name to `SkillName` enum in `src/skills/base.py`.
    - Create a `SkillDefinition` in `src/skills/definitions.py` and add it to `ALL_SKILLS`.
4.  **Handle State**: Create a handler in `src/memory/state_manager.py` and register it in `_SKILL_HANDLERS`.
5.  **Add Routing**: Add an entry to the `TRANSITIONS` map in `src/engine/workflow_transitions.py`.

## Common Mistakes to Avoid

- **Don't put logic in `SkillDefinition`.**
- **Don't hardcode prompts in Python.** Use Jinja2.
- **Don't reuse Output Models.** Each skill should usually have its own specific output structure.
- **Don't forget to register the skill.** The Executor won't find it otherwise.
