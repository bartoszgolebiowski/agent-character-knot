Here is the **Product Requirements Document (PRD)** translated into English. It is structured to focus on business and product logic rather than low-level implementation details.

---

# Product Requirements Document (PRD): StoryGraph AI Agent

| **Project Name** | StoryGraph Agent (POC)                    |
| ---------------- | ----------------------------------------- |
| **Version**      | 1.0                                       |
| **Status**       | Draft / Requirements Definition           |
| **Product Type** | AI Agent / Analytical Tool                |
| **Platform**     | Python (Backend) + HTML (Frontend/Report) |

---

## 1. Executive Summary

The goal of this project is to develop an intelligent AI agent capable of automatically analyzing extensive literary works (up to 100,000 lines of text) to build a dynamic, evolving map of character relationships. Unlike simple sentiment analyzers, this system will understand **causality** (why X relates to Y), identify connections between distant chapters, and provide **textual evidence (quotes)**. The final output is an interactive HTML report based on a navigable tabular structure.

---

## 2. Problem & Solution

### 2.1 The Problem

- In extensive books (sagas, epics), readers or analysts often lose track of complex character relationships.
- It is difficult to track the evolution of relationships over hundreds of pages (e.g., how an alliance in Chapter 3 leads to a betrayal in Chapter 31).
- There are no tools that automatically generate a "book wiki" backed by logic and textual proof.

### 2.2 The Solution

An automated system that "reads" the book chapter by chapter, builds a persistent memory of the world, and generates a clear, navigable report explaining not just **who** relates to whom, but **why** and **on what basis**.

---

## 3. Target Audience & Use Cases

- **Primary User:** Literary analysts, readers of complex sagas, writers (analyzing their own work for consistency), RPG creators looking for lore.
- **Use Case:** The user inputs a `.txt` file containing the entire book -> receives a folder with HTML files where they can click on characters to explore their relationship history.

---

## 4. Key Functional Requirements

### 4.1 Data Ingestion & Processing

- **FR-01 High Volume Support:** The system must stably process text files up to 100,000 lines.
- **FR-02 Intelligent Segmentation (Tool):** The system must automatically detect chapter boundaries (e.g., `CHAPTER`, `PART I`) and provide a tool to extract a specific chapter's text based on the detected structure.
- **FR-03 Sequential Processing:** Analysis must occur chronologically (chapter by chapter) to reflect the natural flow of time in the narrative.

### 4.2 Knowledge Extraction & Core Intelligence (Skills)

- **FR-04 Entity Resolution:** The system must identify characters and merge various aliases for the same person (e.g., "Jon", "Lord Commander", "The Bastard") into a single entity. Merging happens incrementally per chapter.
- **FR-05 Importance Score (No Filtering in POC):** The system may compute an LLM-derived importance score per character for sorting and presentation, but the POC must not filter out characters based on this score.
- **FR-06 Relationship Attribution:** Every detected connection must include:
  - **Relation Type** (Free-form string, e.g., "Secret Alliance").
  - **Reasoning** (Logical explanation of why the relationship exists).
  - **Context** (Brief description of the situation).
  - **Evidence** (Direct quote from the text supporting the claim, plus the chapter number).

- **FR-07 Long-term Reasoning:** The system must link an event in the current chapter to events from the distant past (e.g., "Character X is taking revenge now for a wrong committed in Chapter 3").

### 4.3 Advanced Scaling & Memory (Extended for 100+ Chapters)

- **FR-12 Character-Centric Semantic Dossiers:** The system must maintain refined, non-linear character profiles (Dossiers) that accumulate traits, goals, and evolution summaries. This allows the agent to reason about a character's state at Chapter 101 based on their cumulative development rather than raw history logs.
- **FR-13 Hierarchical Memory Consolidation:** To maintain context over 100+ chapters, the system must periodically consolidate chronological chapter summaries into compressed "Book/Part Summaries."
- **FR-14 Causal Relationship Indexing:** The system must identify and track "Active Causal Nodes" (pivotal interactions like betrothals or betrayals) that persist in the active context as long as they remain narratively relevant, ensuring long-tail relationship consistency.

### 4.4 State Management

- **FR-08 Incremental Updates:** The knowledge graph must be updated after every chapter.
  - **Episodic Memory:** Stores raw events and extractions from the current chapter.
  - **Semantic Memory:** Stores the aggregated character profiles, resolved aliases, and the evolving relationship graph.
- **FR-09 Structured Relationship History (Pydantic):** Relationship entries must follow a Pydantic schema with default values and clear descriptions to ensure downstream compatibility.

### 4.4 Presentation & Output (Tools)

- **FR-10 Multi-Page HTML Report:** The system will generate a set of navigable HTML files using Jinja2 templates.
  - **Character Pages:** Dedicated file for each major character.
  - **Chapter Pages:** Per-chapter pages must include (1) a chapter summary, (2) a list of extracted events, and (3) relationship deltas/changes introduced in that chapter.
- **FR-11 Hyperlink Navigation:** All character names and chapter references must be hyperlinked across the report for seamless navigation.

---

## 5. Technical Implementation (Agent Framework)

### 5.1 Skills vs. Tools

- **Skills (LLM-Driven):** Entity Extraction, Relationship Analysis, Alias Resolution, Importance Scoring (sorting only), Long-term Reasoning.
- **Tools (Deterministic):** Chapter Segmentation, HTML Report Generation, File I/O Management.

### 5.2 Memory Mapping

- **Episodic Memory:** Raw interaction data, chapter-specific event logs.
- **Semantic Memory:** Character registry (canonical names + aliases), Relationship History (Chronological list of interaction objects).
- **Working Memory:** Current chapter text and state-machine context.

---

## 6. Non-Functional Requirements

### 6.1 Accuracy & Quality

- **NFR-01 Hallucination Prevention:** The system must minimize fabricated facts by strictly requiring source text citations (Evidence-Based Extraction).
- **NFR-02 Consistency:** Aliases must be resolved with at least 90% accuracy (avoiding separate profiles for "Gandalf" and "Mithrandir").

### 6.2 Performance & Resources

- **NFR-03 Context Management:** The system must chunk text effectively to stay within LLM token limits while maintaining narrative continuity.
- **NFR-04 Processing Transparency:** As a POC, speed is not critical, but the system should provide progress updates (e.g., "Processing Chapter 5/40").

---

## 7. User Experience (UX) - End Scenario

1. **Index View:** A list of all key characters sorted alphabetically or by "importance" (interaction count).
2. **Character View (Details):**

- **Header:** Main Name + Known Aliases.
- **Traits Section:** Brief character description inferred from actions.
- **Main Relationship Table:**
- _Column 1:_ With Whom? (Link)
- _Column 2:_ Current Relation Status (e.g., Enemy).
- _Column 3:_ Interaction History (Chronological list):
- _Chapter 5:_ Argument over money (Quote: "...")
- _Chapter 12:_ Attempt at reconciliation (Quote: "...")
- _Chapter 40:_ Betrayal (Linked to the event in Chapter 5).

---

## 8. Risks & Constraints

| Risk                   | Description                                                               | Mitigation Strategy                                                                                        |
| ---------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Context Loss**       | The model might forget nuances from the beginning of the book by the end. | Implementation of a "World Chronicle" (condensed registry of key events) passed in every prompt.           |
| **Parsing Errors**     | Non-standard TXT formatting might cause chapter skipping.                 | Requirement for file pre-cleaning or flexible regex patterns.                                              |
| **Character Overload** | In sagas like "War and Peace," the table becomes unreadable.              | UX mitigations only (sorting by importance; search/filter in UI if added later). No data filtering in POC. |
| **API Costs**          | Processing 100k lines via GPT-4 can be expensive.                         | Prompt optimization; use cheaper models for scanning/chunking and advanced models for deduction only.      |

---

## 9. Success Metrics (POC)

1. The system processes the entire book without memory crashes.
2. Navigation in the generated HTML report works smoothly.
3. A randomly selected relationship contains a correct quote and a logical "why" explanation.
4. The main protagonist has all key aliases correctly assigned.
5. The system identifies at least one cause-and-effect link spanning more than 10 chapters.
