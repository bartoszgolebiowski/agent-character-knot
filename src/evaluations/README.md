# Evaluation Framework

A dynamic evaluation system for auditing memory state quality against configurable criteria.

## Overview

This framework allows you to:

1. **Define quality checks** in Markdown files (easy to read and edit)
2. **Dynamically generate** Pydantic validation models from those checks
3. **Use an LLM** to audit JSON state dumps against the criteria
4. **Generate reports** with pass/fail status and detailed reasoning

## Quick Start

### 1. Run an Evaluation

```bash
python run_eval.py \
  --state state/state_dump_final.json \
  --leaderboard src/evaluations/leaderboard/literary_basic.md \
  --output results/evaluation_report.json
```

### 2. Understand the Output

The console will show:

- Overall PASS/FAIL status (based on MUST-HAVE criteria)
- Summary metrics (score percentage, passed/failed counts)
- Detailed results for each check with reasoning

Example:

```
================================================================================
  📊 MEMORY STATE QUALITY EVALUATION REPORT
================================================================================

Overall Status: ✅ PASS

Summary:
  • Total Checks: 3
  • Passed: 3 ✅
  • Failed: 0 ❌
  • Score: 100.0% (3/3)

  • Must-Have Checks: 1/1

--------------------------------------------------------------------------------
Individual Check Results:
--------------------------------------------------------------------------------

LC-001: ✅ PASS
  Reasoning: All character IDs in episodic summaries exist in semantic memory...

LC-002: ✅ PASS
  Reasoning: Relationships include emotional states for both parties...
```

## Architecture

### Components

1. **models.py**: Data structures
   - `CheckDefinition`: Parsed from Markdown
   - `CheckResult`: Individual check outcome
   - `EvaluationResult`: Complete evaluation summary

2. **loader.py**: Markdown parser
   - Extracts check definitions from `.md` files
   - Supports priorities (MUST-HAVE, SHOULD-HAVE, NICE-TO-HAVE)

3. **helpers.py**: Utilities
   - `prune_memory_state()`: Removes large fields to save tokens
   - `calculate_score()`: Computes metrics from results

4. **engine.py**: Core evaluation logic
   - `build_dynamic_evaluation_model()`: Creates Pydantic model at runtime
   - `run_evaluation()`: Orchestrates the complete process

5. **run_eval.py**: CLI runner
   - Loads inputs, runs evaluation, formats report

### Data Flow

```
Markdown File → Loader → CheckDefinitions
                              ↓
JSON State → Pruner → Pruned State
                              ↓
            Dynamic Model Builder (Pydantic)
                              ↓
         Prompt Builder → LLM Client → Structured Output
                              ↓
                  Calculate Score & Status
                              ↓
                    Format Report → Console/JSON
```

## Creating Custom Leaderboards

### Markdown Format

```markdown
# LEADERBOARD CARD: Your Title

## METADATA

| Parameter | Value            |
| --------- | ---------------- |
| System    | Your System Name |
| Version   | 1.0              |

---

## MUST-HAVE CRITERIA

#### LC-001 🔴 MUST-HAVE | Check Name

- **Criterion**: What you're checking
- **Verification**: How to verify it
- **Positive Example**: (Optional) Good example
- **Negative Example**: (Optional) Bad example

---

## SHOULD-HAVE CRITERIA

#### LC-002 🟡 SHOULD-HAVE | Another Check

- **Criterion**: Description
- **Verification**: Verification steps
```

### Priority Levels

- **🔴 MUST-HAVE**: Critical checks. If ANY fail, overall status is FAIL.
- **🟡 SHOULD-HAVE**: Important quality indicators. Don't affect overall PASS/FAIL.
- **🟢 NICE-TO-HAVE**: Optional enhancements.

### Check ID Format

- Pattern: `XX-NNN` (e.g., `LC-001`, `MEM-042`)
- Must be unique within a leaderboard
- Converted to field names (e.g., `LC_001_passed`, `LC_001_reasoning`)

## Advanced Usage

### Custom LLM Configuration

```python
from src.evaluations.engine import run_evaluation
from src.evaluations.loader import parse_leaderboard_markdown
from src.llm.client import LLMClient
from src.llm.config import LLMConfig

# Load checks
checks = parse_leaderboard_markdown("path/to/leaderboard.md")

# Configure custom LLM
config = LLMConfig(
    api_key="your-key",
    model="anthropic/claude-3.5-sonnet",
    temperature=0.0,
    max_output_tokens=8000,
)
client = LLMClient(config=config)

# Run evaluation
result = run_evaluation(
    state_path="state/state_dump.json",
    checks=checks,
    llm_client=client,
)
```

### Programmatic Access

```python
from src.evaluations.engine import run_evaluation
from src.evaluations.loader import parse_leaderboard_markdown

checks = parse_leaderboard_markdown("leaderboard.md")
result = run_evaluation("state.json", checks)

# Access structured data
print(f"Score: {result.score_percentage}%")
print(f"Status: {result.overall_status}")

for check in result.check_results:
    if not check.passed:
        print(f"{check.check_id} failed: {check.reasoning}")
```

## Design Principles

1. **Separation of Concerns**: Checks are data (Markdown), not code
2. **Dynamic Models**: Pydantic models are generated at runtime based on loaded checks
3. **Token Efficiency**: State pruning removes large text fields before LLM call
4. **Deterministic Scoring**: Overall PASS requires 100% of MUST-HAVE checks to pass
5. **Extensible**: Add new checks without changing code—just edit the Markdown file

## Example Leaderboards

- `literary_basic.md`: Basic checks for literary memory (character consistency, relationship quality)

## Troubleshooting

### "No valid checks found"

- Ensure your Markdown follows the exact format (check spacing, headers)
- Verify check IDs match pattern `XX-NNN`

### LLM returns unexpected format

- Check that Criterion and Verification fields are detailed enough
- Increase `max_output_tokens` if reasoning is truncated

### High token usage

- Review pruned state size (should exclude `current_chapter_text` and `chapter_map`)
- Consider reducing number of checks or splitting into multiple leaderboards
