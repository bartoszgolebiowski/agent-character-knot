# LEADERBOARD CARD: STORYGRAPH AI AGENT

## METADATA

| Parameter   | Value                     |
| ----------- | ------------------------- |
| System      | StoryGraph AI Agent       |
| Target Text | War and Peace (Benchmark) |
| Version     | 1.0                       |

---

## MUST-HAVE CRITERIA (System Integrity)

#### SG-003 🔴 MUST-HAVE | Canonical Entity Resolution

- **Criterion**: Aliases must resolve to a single canonical `CharacterProfile`. Major protagonists must not have duplicate profiles.
- **Verification**: Query `AgentState.semantic.characters`. Verify that "Prince Andrew", "Bolkónski", and "André" resolve to the same UUID, and "Pierre" and "Bezúkhov" resolve to the same UUID.
- **Positive Example**: Looking up "André" in `alias_index` returns the same UUID as looking up "Bolkónski".
- **Negative Example**: Semantic memory contains two distinct profiles: one for "Prince Andrew" and another for "Bolkónski".

#### SG-004 🔴 MUST-HAVE | Structured Relationship Attribution

- **Criterion**: Relationship entries must be stored as structured Pydantic models containing specific types, reasoning, and verbatim evidence.
- **Verification**: Inspect `AgentState.semantic.relationships`. Every `RelationshipInteraction` must have a non-null `relation_type`, `reasoning`, and a valid `RelationshipEvidence` object with a quote length > 10.
- **Positive Example**: Relationship includes `relation_type="Political Rivalry"`, `reasoning` is detailed, and `evidence.quote` is a direct string from the text.
- **Negative Example**: `relation_type` is generic (e.g., "Related") or `evidence` is missing/null.

#### SG-005 🔴 MUST-HAVE | Sequential State Integrity

- **Criterion**: Knowledge must build incrementally in ascending chronological order; the graph must utilize extraction results from previous chapters.
- **Verification**: Check the `extracted_at` timestamps or order of `interactions` in `RelationshipHistory`. They must follow the sequence of `chapter_index` 0, 1, 2, etc.
- **Positive Example**: Interaction history shows Chapter 1 events appearing before Chapter 2 events in the list.
- **Negative Example**: Chapter 5 events appear in the list before Chapter 1 events, or state appears overwritten rather than appended.

#### SG-006 🔴 MUST-HAVE | Artifact Generation

- **Criterion**: The system must produce the physical HTML files required for the report structure.
- **Verification**: Verify the existence of `index.html`, `static/style.css`, and sub-pages for characters (`character-{uuid}.html`) and chapters (`chapter-{num}.html`) in the output directory.
- **Positive Example**: Output directory contains `index.html`, 150+ character HTML files, and 361 chapter HTML files.
- **Negative Example**: Output directory is empty or contains only `index.html` with broken links.

---

## SHOULD-HAVE CRITERIA (Intelligence & Depth)

#### SG-007 🟡 SHOULD-HAVE | Long-Term Causality

- **Criterion**: The agent must identify causal links between events spanning a significant gap (e.g., >10 chapters).
- **Verification**: Inspect `RelationshipInteraction` models for the `references_event_id` field or explicit reasoning linking disparate chapters.
- **Positive Example**: An interaction in Chapter 40 cites a `past_event_id` from Chapter 3 as the cause of the current conflict.
- **Negative Example**: No `references_event_id` are populated across the entire semantic memory.

#### SG-008 🟡 SHOULD-HAVE | Character Evolution

- **Criterion**: Character profiles should track psychological changes over time, not just static traits.
- **Verification**: Inspect `CharacterProfile.evolution_summary`. It should describe a trajectory or change in state.
- **Positive Example**: "Pierre begins as a socially awkward outcast but evolves into a confident seeker of truth after his inheritance."
- **Negative Example**: Summary only lists physical attributes like "Fat, wears glasses" or is empty.

#### SG-009 🟡 SHOULD-HAVE | Hierarchical Memory Consolidation

- **Criterion**: The system consolidates detailed chapter events into high-level summaries to manage context window limits.
- **Verification**: Inspect `AgentState.semantic.book_summaries`. It should contain high-level summaries representing blocks of chapters (e.g., Book 1, Book 2).
- **Positive Example**: `book_summaries` list has entries, and token usage per chapter processing remained stable.
- **Negative Example**: `book_summaries` is empty, or processing logs show linear growth in prompt tokens.

#### SG-010 🟡 SHOULD-HAVE | Importance Ranking

- **Criterion**: Characters must be correctly ranked by narrative weight using the `importance_score`.
- **Verification**: Check `AgentState.semantic.characters`. Protagonists (Pierre, Natasha, Andrew) should have scores > 0.9, while named servants/extras should be < 0.2.
- **Positive Example**: Pierre Bezúkhov: 1.0, Footman: 0.1.
- **Negative Example**: All characters have the same score (e.g., 0.0 or 1.0), or a minor character is ranked higher than a protagonist.

#### SG-011 🟡 SHOULD-HAVE | Hyperlink Navigation

- **Criterion**: The generated HTML report must function as a browsable wiki with internal linking.
- **Verification**: In the generated HTML, character names within relationship tables and summaries must be `<a>` tags pointing to valid character pages.
- **Positive Example**: `<a href="char_uuid.html">Pierre</a>` appears in the text description of an event.
- **Negative Example**: Character names appear as plain text without hyperlinks.

#### SG-012 🟡 SHOULD-HAVE | Active Causal Indexing

- **Criterion**: The agent flags unresolved relationship tensions or open plot loops.
- **Verification**: Inspect `RelationshipInteraction` models for instances where `is_causal_node=True`.
- **Positive Example**: A betrayal is marked as `is_causal_node=True` and `resolved_in_chapter=None` until a later chapter resolves it.
- **Negative Example**: All interactions default to `is_causal_node=False`.
