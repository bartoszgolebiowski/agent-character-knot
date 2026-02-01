# FR-07: Long-term Reasoning

**Status:** Not Started  
**Priority:** High  
**Epic:** Knowledge Extraction & Core Intelligence  
**Story Points:** 8

---

## Description

The system must be capable of linking events across distant chapters to detect causal relationships and long-term narrative arcs. This is what elevates the agent from a simple "chapter summarizer" to a true analytical tool.

Examples of long-term reasoning:

- "Character X's betrayal in Chapter 40 is revenge for the insult they suffered in Chapter 3"
- "The alliance formed in Chapter 5 directly led to the war declaration in Chapter 28"
- "Character Y's distrust of Z (seen in Chapter 50) stems from witnessing Z's cruelty in Chapter 12"

This requires the system to:

1. Retain context from early chapters (via semantic memory)
2. Recognize when a current event references a past event
3. Explicitly link the two with evidence from both chapters

This is the **hardest technical challenge** because LLMs have limited context windows and may forget details from hundreds of pages ago.

---

## Acceptance Criteria

### Business Criteria

1. **AC-1:** The system successfully identifies at least one cause-and-effect link spanning more than 10 chapters in a test book.

2. **AC-2:** When a long-term link is detected, the relationship entry includes:
   - Reference to the past event (chapter number + brief description)
   - Evidence quote from the past chapter
   - Evidence quote from the current chapter
   - Explicit reasoning connecting the two

3. **AC-3:** The HTML report displays cross-chapter links as hyperlinks (clicking on "See Chapter 3" navigates to that chapter's page).

4. **AC-4:** The system doesn't hallucinate false connections - all claimed links must be supported by textual evidence from both chapters.

5. **AC-5:** Long-term links are preserved in the relationship history and visible in the timeline view.

---

## Technical Description

### Implementation Approach

Long-term reasoning requires a **hybrid approach**:

1. **Semantic Memory:** Stores condensed event summaries from all past chapters
2. **Episodic Memory:** Retains full details for recent chapters (rolling window)
3. **LLM Skill:** Analyzes current chapter while referencing past event registry

#### 1. **Event Registry in Semantic Memory (`src/memory/models.py`)**

```python
class SignificantEvent(BaseModel):
    """A major plot event stored for long-term reference."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    chapter_index: int = Field(description="Chapter where event occurred")
    chapter_title: str = Field(description="Chapter title for display")
    description: str = Field(
        description="Brief summary of the event (1-2 sentences)"
    )
    involved_characters: list[str] = Field(
        default_factory=list,
        description="Character IDs of those involved"
    )
    evidence_quote: str = Field(
        description="Key quote demonstrating this event"
    )
    significance: Literal["major", "moderate", "minor"] = Field(
        description="Narrative importance of this event"
    )

class SemanticMemory(BaseModel):
    characters: dict[str, CharacterProfile] = Field(default_factory=dict)
    alias_index: dict[str, str] = Field(default_factory=dict)
    relationships: dict[str, dict[str, RelationshipHistory]] = Field(default_factory=dict)

    event_chronicle: list[SignificantEvent] = Field(
        default_factory=list,
        description="Timeline of major events across all chapters"
    )
```

#### 2. **Output Models (`src/skills/models.py`)**

```python
class EventExtractionOutput(BaseModel):
    """Significant events from a chapter to store in chronicle."""
    events: list[SignificantEvent] = Field(
        description="Major events worth remembering long-term"
    )

class CausalLink(BaseModel):
    """A detected cause-and-effect relationship across chapters."""
    past_event_id: str = Field(
        description="ID of the historical event that caused current situation"
    )
    current_chapter_index: int
    connection_type: str = Field(
        description="Nature of causal link (e.g., 'Revenge', 'Consequence', 'Callback')"
    )
    reasoning: str = Field(
        description="Explanation of how the past event led to the current situation"
    )
    current_evidence_quote: str = Field(
        description="Quote from current chapter showing the connection"
    )

class LongTermReasoningOutput(BaseModel):
    """Result of analyzing current chapter for long-term connections."""
    causal_links: list[CausalLink] = Field(
        default_factory=list,
        description="Detected cross-chapter causal relationships"
    )
    reasoning_summary: str = Field(
        description="Overall explanation of long-term narrative threads"
    )
```

#### 3. **Two-Stage Skill Approach**

**Skill 1: Event Extraction (per chapter)**

Template: `src/prompting/jinja/skills/extract_events.j2`

```jinja
You are analyzing a chapter to identify significant events worth remembering.

# Current Chapter
{{ working.current_chapter_title }}
```

{{ working.current_chapter_text }}

```

# Task
Extract 3-5 major events from this chapter that might be referenced later in the story.

Focus on:
- Plot-driving actions (betrayals, alliances, discoveries)
- Character-defining moments (moral choices, revelations)
- Events that create future obligations or debts

# Output Format
Provide EventExtractionOutput with brief descriptions and evidence quotes.
```

**Skill 2: Long-Term Reasoning (per chapter)**

Template: `src/prompting/jinja/skills/long_term_reasoning.j2`

```jinja
You are analyzing a chapter to detect if current events connect to past events.

# Current Chapter
{{ working.current_chapter_title }}
```

{{ working.current_chapter_text[:3000] }}

```

# Event Chronicle (Past Significant Events)
{% for event in semantic.event_chronicle %}
## Event {{ loop.index }} ({{ event.chapter_title }})
- **Description:** {{ event.description }}
- **Involved:** {{ event.involved_characters | map('get_char_name', semantic.characters) | join(', ') }}
- **Evidence:** "{{ event.evidence_quote }}"
- **Event ID:** {{ event.event_id }}
{% endfor %}

# Task
Analyze the current chapter to determine if any actions/situations are:
1. Direct consequences of past events
2. Motivated by past events (e.g., revenge)
3. Callbacks or references to past events

For each connection found:
- Cite the past event ID
- Explain the causal relationship
- Provide evidence from BOTH the past event (already in chronicle) and current chapter

# Critical Rules
- Only link events if there's clear textual evidence
- Don't create tenuous connections based on speculation
- Prefer explicit references ("remembering when...", "because of...")

# Output Format
Provide LongTermReasoningOutput with all detected causal links.
```

#### 4. **State Update Handlers (`src/memory/state_manager.py`)**

```python
def append_event_chronicle(
    state: AgentState,
    output: EventExtractionOutput
) -> AgentState:
    """Add significant events to long-term memory."""
    new_state = deepcopy(state)
    new_state.semantic.event_chronicle.extend(output.events)
    return new_state

def integrate_causal_links(
    state: AgentState,
    output: LongTermReasoningOutput
) -> AgentState:
    """
    Integrate detected causal links into relationship history.

    For each causal link:
    1. Retrieve the past event from chronicle
    2. Create a special relationship interaction that references both chapters
    3. Append to relationship history with cross-references
    """
    new_state = deepcopy(state)

    for link in output.causal_links:
        # Find the past event
        past_event = next(
            (e for e in new_state.semantic.event_chronicle if e.event_id == link.past_event_id),
            None
        )

        if not past_event:
            logger.warning(f"Past event {link.past_event_id} not found")
            continue

        # Create a special interaction entry that links both chapters
        for char_id in past_event.involved_characters:
            # (Add logic to update relationships with cross-chapter reference)
            # This could be stored in a separate "causal_links" field
            # or integrated into relationship interactions with a "references" field
            pass

    return new_state

_SKILL_HANDLERS = {
    SkillName.EXTRACT_EVENTS: append_event_chronicle,
    SkillName.LONG_TERM_REASONING: integrate_causal_links,
    # ... other handlers
}
```

#### 5. **Workflow Integration**

In `src/engine/workflow_transitions.py`:

```python
TRANSITIONS = {
    # After analyzing chapter relationships...
    WorkflowStage.RELATIONSHIP_EXTRACTION: Decision.llm(SkillName.EXTRACT_EVENTS),
    WorkflowStage.EXTRACT_EVENTS: Decision.llm(SkillName.LONG_TERM_REASONING),
    WorkflowStage.LONG_TERM_REASONING: Decision.internal("advance_to_next_chapter"),
    # ...
}
```

#### 6. **Memory Optimization**

To handle 100k lines without hitting context limits:

**Strategy 1: Selective Chronicle**

- Only store "major" significance events (filter by importance)
- Limit to top 100 events across the entire book

**Strategy 2: Chapter Summaries**

- Instead of full event details, store condensed summaries
- Reference full text only when a link is detected

**Strategy 3: Retrieval-Augmented Generation (RAG)**

- Store all events in a vector database
- Retrieve only relevant past events based on semantic similarity to current chapter
- (Advanced - may be out of scope for POC)

#### 7. **HTML Display**

In relationship interaction template:

```html
{% if interaction.causal_link %}
<div class="causal-link-badge">
  <strong>🔗 Long-term Connection</strong>
  <p>
    This event connects to
    <a href="chapter-{{ interaction.causal_link.past_chapter }}.html">
      Chapter {{ interaction.causal_link.past_chapter }}
    </a>
  </p>
  <details>
    <summary>Show Details</summary>
    <p>
      <strong>Past Event:</strong> {{
      interaction.causal_link.past_event_description }}
    </p>
    <blockquote>"{{ interaction.causal_link.past_evidence }}"</blockquote>
    <p><strong>Connection:</strong> {{ interaction.causal_link.reasoning }}</p>
  </details>
</div>
{% endif %}
```

### Architecture Compliance

- **Two LLM Skills:** Event extraction + causal reasoning (separate concerns)
- **Semantic Memory:** Event chronicle stored centrally
- **State Immutability:** All updates via `state_manager` handlers
- **No LLM Routing:** Coordinator decides when to run long-term reasoning
- **Evidence-Based:** All links require quotes from both chapters

### Testing Strategy

1. **Unit Test:** Verify event chronicle appending and causal link integration
2. **Integration Test:** Create a synthetic 20-chapter story with a known causal chain:
   - Chapter 5: Character A insults Character B
   - Chapter 18: Character B betrays Character A
   - Verify system detects the connection

3. **Accuracy Test:** Manually review detected causal links in a real book:
   - Check for false positives (hallucinated connections)
   - Check for false negatives (missed obvious connections)

4. **Scale Test:** Verify event chronicle doesn't grow unbounded (stays under token limits)

---

## Dependencies

- `FR-01` (High Volume Support) - Need efficient memory management
- `FR-06` (Relationship Attribution) - Causal links integrate with relationships
- LLM with strong long-context capabilities (Claude 3.5 Sonnet preferred)

---

## Questions / Clarifications Needed

- Should the event chronicle have a maximum size (e.g., top 100 events), or grow unbounded?
- Do we need a separate UI view for the "timeline of events" independent of character pages?
- Should we implement RAG (vector database) for event retrieval, or rely on full context for POC?
- What should happen if the LLM detects a connection but can't find the event ID in the chronicle?
- Should we support multi-hop reasoning (Event A → Event B → Event C), or only direct links?
