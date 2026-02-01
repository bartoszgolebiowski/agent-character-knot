# FR-02: Intelligent Segmentation (Tool)

**Status:** Not Started  
**Priority:** High  
**Epic:** Data Ingestion & Processing  
**Story Points:** 3

---

## Description

The system must automatically detect chapter boundaries in unstructured text files without requiring manual preprocessing from the user. Books come in various formats - some use "CHAPTER I", others "Part 1", "BOOK ONE", or even numbered sections. The segmentation tool needs to be intelligent enough to handle common patterns while remaining flexible for edge cases.

This is a **deterministic tool** (not an LLM skill) because:
- Pattern matching is faster and cheaper than LLM calls
- Results must be 100% reproducible
- No "understanding" is needed - just structural parsing

The tool provides the foundation for sequential processing by giving the system a clear map of where each chapter begins and ends.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The system correctly detects chapter boundaries in at least 3 different book formats:
   - Numbered chapters (e.g., "CHAPTER 1", "CHAPTER I")
   - Named parts (e.g., "PART ONE: The Beginning")
   - Mixed formats (e.g., "BOOK II - CHAPTER 5")

2. **AC-2:** The tool returns a structured list of chapter metadata including:
   - Chapter number/index
   - Chapter title (if present)
   - Start line number
   - End line number

3. **AC-3:** When no chapter markers are detected, the system provides a fallback strategy (e.g., treat the entire file as one chapter OR split by fixed line counts).

4. **AC-4:** The tool handles edge cases gracefully:
   - Empty lines between chapters
   - All-caps vs. title case chapter markers
   - Non-standard spacing and formatting

5. **AC-5:** Processing the test file "War and Peace" (which uses "CHAPTER" markers) results in exactly 361 detected chapters.

---

## Technical Description

### Implementation Approach

#### 1. **Tool Structure (`src/tools/chapter_segmentation.py`)**

Following the Tools layer guidelines:

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from pydantic import BaseModel, Field

# Input Model
class ChapterSegmentationRequest(BaseModel):
    """Request to segment a book into chapters."""
    file_path: str = Field(description="Absolute path to the text file")
    patterns: list[str] = Field(
        default=[
            r"^CHAPTER\s+[IVXLCDM\d]+",  # Roman/Arabic numerals
            r"^PART\s+[IVXLCDM\d]+",
            r"^BOOK\s+[IVXLCDM\d]+",
        ],
        description="Regex patterns to match chapter headers"
    )

# Output Model
class ChapterMetadata(BaseModel):
    """Metadata for a single chapter."""
    index: int = Field(description="Zero-based chapter index")
    title: str = Field(description="Chapter title/header text")
    start_line: int = Field(description="1-based line number where chapter starts")
    end_line: int = Field(description="1-based line number where chapter ends")
    line_count: int = Field(description="Total lines in this chapter")

class ChapterSegmentationResult(BaseModel):
    """Result of chapter segmentation."""
    chapters: list[ChapterMetadata]
    total_chapters: int
    total_lines: int
    fallback_used: bool = Field(
        default=False,
        description="True if no chapters detected and fallback applied"
    )

# Tool Client
@dataclass(frozen=True, slots=True)
class ChapterSegmentationTool:
    """Deterministic tool for detecting chapter boundaries."""
    
    def execute(self, request: ChapterSegmentationRequest) -> ChapterSegmentationResult:
        """
        Scan file for chapter markers and return boundary metadata.
        
        Algorithm:
        1. Read file line by line
        2. Match each line against regex patterns
        3. Record start positions
        4. Compute end positions (previous to next chapter start)
        5. Handle final chapter (ends at EOF)
        """
        path = Path(request.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {request.file_path}")
        
        # Compile patterns
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in request.patterns]
        
        # Scan file
        chapter_markers = []  # List of (line_num, title)
        with path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line_stripped = line.strip()
                for pattern in compiled_patterns:
                    if pattern.match(line_stripped):
                        chapter_markers.append((line_num, line_stripped))
                        break
        
        total_lines = line_num  # From last iteration
        
        # Build chapter metadata
        chapters = []
        for idx, (start_line, title) in enumerate(chapter_markers):
            # End line is either next chapter start - 1, or EOF
            end_line = (
                chapter_markers[idx + 1][0] - 1
                if idx + 1 < len(chapter_markers)
                else total_lines
            )
            chapters.append(
                ChapterMetadata(
                    index=idx,
                    title=title,
                    start_line=start_line,
                    end_line=end_line,
                    line_count=end_line - start_line + 1,
                )
            )
        
        # Fallback: if no chapters found, treat whole file as 1 chapter
        fallback = False
        if not chapters:
            fallback = True
            chapters.append(
                ChapterMetadata(
                    index=0,
                    title="Complete Text",
                    start_line=1,
                    end_line=total_lines,
                    line_count=total_lines,
                )
            )
        
        return ChapterSegmentationResult(
            chapters=chapters,
            total_chapters=len(chapters),
            total_lines=total_lines,
            fallback_used=fallback,
        )
```

#### 2. **State Integration**

In `src/memory/models.py`, add to `WorkingMemory`:
```python
class WorkingMemory(BaseModel):
    chapter_map: list[ChapterMetadata] = Field(default_factory=list)
    # ... existing fields
```

In `src/memory/state_manager.py`:
```python
def ingest_chapter_segmentation(
    state: AgentState,
    result: ChapterSegmentationResult
) -> AgentState:
    new_state = deepcopy(state)
    new_state.working.chapter_map = result.chapters
    new_state.working.total_chapters = result.total_chapters
    return new_state
```

#### 3. **Workflow Integration**

In `src/engine/types.py`, add:
```python
class ToolName(str, Enum):
    CHAPTER_SEGMENTATION = "chapter_segmentation"
```

In `src/engine/workflow_transitions.py`:
```python
from src.engine.types import WorkflowStage, ToolName

TRANSITIONS = {
    WorkflowStage.INIT: Decision.tool(ToolName.CHAPTER_SEGMENTATION),
    # After segmentation, move to chapter loading
    WorkflowStage.SEGMENTATION_COMPLETE: Decision.tool(ToolName.CHAPTER_EXTRACTION),
    # ...
}
```

#### 4. **Agent Execution**

In `src/agent.py`, handle tool execution:
```python
if decision.action_type == ActionType.TOOL:
    if decision.tool_name == ToolName.CHAPTER_SEGMENTATION:
        tool = ChapterSegmentationTool()
        request = ChapterSegmentationRequest(
            file_path=state.working.input_file_path
        )
        result = tool.execute(request)
        state = state_manager.ingest_chapter_segmentation(state, result)
```

### Architecture Compliance

- **No LLM calls:** Pure Python regex processing
- **Pydantic models:** All I/O uses Pydantic for validation
- **Immutable state:** Handler uses `deepcopy(state)`
- **Registered in state_manager:** Output ingestion follows standard pattern
- **Typed enums:** Uses `ToolName` enum from `types.py`

### Testing Strategy

1. **Unit Test:** Test with synthetic files containing different chapter formats
2. **Integration Test:** Run on "War and Peace" and verify 361 chapters detected
3. **Edge Case Tests:**
   - File with no chapter markers (verify fallback)
   - File with only 1 chapter
   - File with inconsistent formatting (mixed case, extra spaces)

---

## Dependencies

- Python standard library (`re`, `pathlib`)
- Existing Pydantic models

---

## Questions / Clarifications Needed

- Should the tool support user-provided custom regex patterns via configuration file?
- What should happen if a book has nested structures (e.g., "BOOK I" containing "CHAPTER 1-5")? Should we detect both levels or only the finest granularity?
- Should we validate that chapters are sequential and non-overlapping, or trust the regex output?
