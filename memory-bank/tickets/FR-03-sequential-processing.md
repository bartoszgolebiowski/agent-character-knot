# FR-03: Sequential Processing

**Status:** Not Started  
**Priority:** High  
**Epic:** Data Ingestion & Processing  
**Story Points:** 3

---

## Description

The system must process chapters in chronological order (Chapter 1 → Chapter 2 → Chapter 3...) to preserve the natural narrative flow and temporal causality. This is critical for accurate relationship tracking because:

- Character introductions happen in specific chapters
- Relationships evolve over time (ally → enemy → reconciliation)
- Later events reference earlier events (revenge for a Chapter 3 betrayal happening in Chapter 30)

Processing out of order would destroy this causal chain and make "long-term reasoning" (FR-07) impossible. The workflow must enforce this ordering through the state machine, not rely on the LLM or external tools to maintain sequence.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The system processes all chapters in ascending numerical order (chapter index 0, 1, 2, ... N-1).
2. **AC-2:** Each chapter's analysis has access to the cumulative knowledge from all previous chapters (via `AgentState.semantic`).
3. **AC-3:** The system never skips a chapter or processes chapters in parallel.
4. **AC-4:** Progress logs confirm sequential processing (e.g., "Processing Chapter 1/40", "Processing Chapter 2/40", etc.).
5. **AC-5:** If processing is interrupted, the system can report which chapter was being processed when it stopped.

---

## Technical Description

### Implementation Approach

Following the state-driven architecture, sequential processing is enforced by the **Coordinator** using the workflow state machine.

#### 1. **State Machine Design**

In `src/engine/types.py`, define workflow stages:
```python
from enum import Enum

class WorkflowStage(str, Enum):
    INIT = "init"
    SEGMENTATION = "segmentation"
    LOAD_CHAPTER = "load_chapter"
    ANALYZE_CHAPTER = "analyze_chapter"
    UPDATE_SEMANTIC = "update_semantic"
    CHECK_COMPLETION = "check_completion"
    GENERATE_REPORT = "generate_report"
    COMPLETE = "complete"
```

#### 2. **Coordinator Logic**

In `src/engine/coordinator.py`:
```python
from src.engine.types import WorkflowStage, ActionType
from src.memory.models import AgentState
from src.engine.decision import CoordinatorDecision

class Coordinator:
    """State machine that decides next action based on current stage."""
    
    def next_action(self, state: AgentState) -> CoordinatorDecision:
        """
        Lookup next action from TRANSITIONS table.
        Sequential processing is enforced by looping through chapters.
        """
        stage = state.workflow.current_stage
        
        # Special case: Chapter iteration logic
        if stage == WorkflowStage.CHECK_COMPLETION:
            current_idx = state.working.current_chapter_index
            total = state.working.total_chapters
            
            if current_idx < total - 1:
                # More chapters to process -> loop back
                return CoordinatorDecision.tool(
                    tool_name=ToolName.CHAPTER_EXTRACTION,
                    context={"next_chapter": current_idx + 1}
                )
            else:
                # All chapters done -> proceed to report generation
                return CoordinatorDecision.tool(
                    tool_name=ToolName.HTML_REPORT_GENERATION
                )
        
        # Default: Lookup from transitions table
        from src.engine.workflow_transitions import TRANSITIONS
        return TRANSITIONS.get(stage, CoordinatorDecision.noop())
```

#### 3. **Workflow Transitions Map**

In `src/engine/workflow_transitions.py`:
```python
from src.engine.types import WorkflowStage, ToolName, SkillName
from src.engine.decision import CoordinatorDecision as Decision

TRANSITIONS: dict[WorkflowStage, Decision] = {
    WorkflowStage.INIT: Decision.tool(ToolName.CHAPTER_SEGMENTATION),
    
    WorkflowStage.SEGMENTATION: Decision.tool(ToolName.CHAPTER_EXTRACTION),
    
    WorkflowStage.LOAD_CHAPTER: Decision.llm(SkillName.ANALYZE_CHAPTER),
    
    WorkflowStage.ANALYZE_CHAPTER: Decision.llm(SkillName.EXTRACT_ENTITIES),
    
    WorkflowStage.UPDATE_SEMANTIC: Decision.internal("update_knowledge_graph"),
    
    # After update, check if more chapters remain
    WorkflowStage.CHECK_COMPLETION: Decision.internal("check_loop_condition"),
    
    WorkflowStage.GENERATE_REPORT: Decision.tool(ToolName.HTML_REPORT_GENERATION),
    
    WorkflowStage.COMPLETE: Decision.complete("Processing finished"),
}
```

#### 4. **State Updates for Iteration**

In `src/memory/state_manager.py`:
```python
def advance_to_next_chapter(state: AgentState) -> AgentState:
    """Increment chapter index and reset working memory for next iteration."""
    new_state = deepcopy(state)
    new_state.working.current_chapter_index += 1
    new_state.working.current_chapter_text = ""  # Clear for next load
    new_state.workflow.current_stage = WorkflowStage.LOAD_CHAPTER
    return new_state

def complete_chapter_analysis(state: AgentState, analysis_output: AnalysisOutput) -> AgentState:
    """Store analysis results and advance workflow."""
    new_state = deepcopy(state)
    
    # Store in episodic memory
    new_state.episodic.raw_events.extend(analysis_output.events)
    
    # Advance workflow
    new_state.workflow.current_stage = WorkflowStage.UPDATE_SEMANTIC
    
    return new_state
```

#### 5. **Main Agent Loop**

In `src/agent.py`:
```python
class Agent:
    def run(self, initial_state: AgentState) -> AgentState:
        """Main execution loop - processes chapters sequentially."""
        state = initial_state
        max_iterations = 10000  # Safety limit
        
        for iteration in range(max_iterations):
            # Get next decision from coordinator
            decision = self.coordinator.next_action(state)
            
            # Log progress
            if state.workflow.current_stage == WorkflowStage.ANALYZE_CHAPTER:
                logger.info(
                    f"Processing Chapter {state.working.current_chapter_index + 1}"
                    f"/{state.working.total_chapters}"
                )
            
            # Execute decision
            if decision.action_type == ActionType.COMPLETE:
                logger.info("Workflow complete")
                return state
            
            elif decision.action_type == ActionType.LLM:
                result = self.executor.execute(decision.skill_name, state)
                state = self.state_manager.ingest_skill_output(state, result)
            
            elif decision.action_type == ActionType.TOOL:
                result = self._execute_tool(decision, state)
                state = self.state_manager.ingest_tool_output(state, result)
            
            # Safety check
            if iteration == max_iterations - 1:
                logger.error("Max iterations reached - possible infinite loop")
                break
        
        return state
```

#### 6. **Preventing Out-of-Order Processing**

The architecture enforces ordering through:
- **Single-threaded execution:** No parallel chapter processing
- **State machine control:** Coordinator decides when to load next chapter
- **Index increment:** Only happens after current chapter is fully processed
- **No LLM control:** LLM never decides which chapter to process

### Architecture Compliance

- **Coordinator decides flow:** Uses `TRANSITIONS` table + loop logic
- **No side effects in Coordinator:** Pure function returning `Decision`
- **State immutability:** All updates via `state_manager` with `deepcopy`
- **Typed enums:** Uses `WorkflowStage`, `ToolName`, `SkillName` from `types.py`
- **Separation of concerns:** Chapter loading (tool), analysis (skill), sequencing (coordinator)

### Testing Strategy

1. **Integration Test:** Process a 10-chapter book and verify:
   - Chapters are processed 0 → 9
   - Log shows sequential progress
   - Final state contains knowledge from all chapters

2. **State Machine Test:** Unit test `Coordinator.next_action()` with mock states at different chapters

3. **Edge Case Tests:**
   - Single-chapter book (no iteration)
   - Empty book (no chapters after segmentation)

---

## Dependencies

- `FR-02` (Chapter Segmentation) must be complete to provide chapter count
- `WorkflowStage` enum in `src/engine/types.py`
- Logging configuration in `src/logger.py`

---

## Questions / Clarifications Needed

- Should we implement checkpointing to resume from a specific chapter if processing is interrupted?
- Is there a maximum processing time per chapter before we should timeout and skip?
- Should we support a "dry run" mode that validates chapter detection without full analysis?
