# PawPal+ System Design

## System Diagram

```
┌──────────────────────────────┐
│        User (Human)          │
│  - Inputs tasks manually     │
│  - Types plain-English text  │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│        Streamlit UI          │
│  - Smart Task Input (text)  │
│  - Manual form entry        │
│  - Calendar view (Day/Week) │
│  - Displays schedule        │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│        Input Parser          │
│  - Splits text into lines    │
│  - Skips blank/short lines   │
│  - Detects pet name per line │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│   Retrieval Module (RAG)     │
│  - Loads knowledge_base.md   │
│  - Keyword-matches each line │
│  - Returns relevant rules    │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│   Groq API (Llama 3 8B)      │
│  - Receives KB slice + task  │
│  - Returns priority/category │
│  - Cites rule as reason      │
│  - Falls back to rules if ↓  │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│   Task Classifier            │
│  - Infers duration & time    │
│  - Finds available time slot │
│  - Parses frequency/date     │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│   Validation + Scheduler     │
│  - Validates task fields     │
│  - Detects time conflicts    │
│  - Enforces NON_NEGOTIABLE   │
│  - Priority sorts the plan   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│     Schedule Output Layer    │
│  - Organized by day/week     │
│  - Color-coded priorities    │
│  - Conflict warnings in UI   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│   Human + Testing Layer      │
│  - User reviews schedule     │
│  - Edits or marks complete   │
│  - Pytest validates logic    │
└──────────────────────────────┘
```

---

## What Each Layer Does

### 1. User (Human)
The owner enters tasks in plain English using the Smart Task Input box, or fills out a manual form with structured fields. There is no file upload currently — input is text typed directly into Streamlit.

### 2. Streamlit UI (`app.py`)
Handles all interaction. Provides two input paths (smart text vs. manual form), a color-coded weekly calendar via `streamlit_calendar`, and a task list view with edit/delete/complete buttons. Uses `st.session_state` to hold owner, pets, and tasks across rerenders.

### 3. Input Parser (`rag_helper.py` → `parse_input`)
Splits the raw text block into individual lines, strips whitespace, and drops lines that are too short to be meaningful. In multi-pet mode, each line is also scanned for a pet name so tasks can be routed to the right pet automatically.

### 4. Retrieval Module — RAG (`rag_helper.py` → `retrieve_context`)
Loads `knowledge_base.md` (33 lines of domain rules covering priority, duration, and time defaults). For each task line, it tokenizes the text and checks which topic categories match using a hardcoded keyword dictionary (10 topics: medication, vet, feeding, walk, grooming, play, training, time, schedule, health). Only the matching KB lines are passed forward — the full knowledge base is never sent to the classifier. This is the "retrieval" step of RAG.

### 5. Task Classifier (`rag_helper.py` → `classify_task`)

**Priority and category** are now determined by **Groq (Llama 3 8B)**. The retrieved KB lines and the task string are sent to the model, which returns priority, category, and a one-sentence reason citing the rule it used. If the API call fails or no key is set, the pipeline falls back to the original keyword heuristics silently.

**Duration, time, frequency, and date range** are still handled deterministically:
- **Duration**: extracted from "for 30 minutes"; otherwise the category default is used (meds=5 min, feeding=10, walk=30, vet=60, grooming=20, play/training=20)
- **Scheduled time**: extracted from "at X:XXpm", or inferred from time words (morning=08:00, after breakfast=08:30, afternoon=14:00, evening=18:00, night=21:00); if no time is given, the pipeline finds the next available slot starting from a category default (grooming=10:00, play=15:00, training=17:00) to avoid conflicts
- **Frequency + date range**: "next [weekday]" → one-time event, "every Saturday" → weekly on that day, default → daily for 30 days

### 6. Validation + Scheduler (`pawpal_system.py` → `Scheduler`)
Takes the parsed `Task` objects and:
- Sorts by priority tier so `non-negotiable` tasks always appear first
- Calls `detect_conflicts()` to find tasks that overlap in time on the same day
- Builds a weekly schedule mapping each day of the week to its applicable tasks, respecting `start_date`/`end_date` windows and `frequency` rules

### 7. Schedule Output Layer (`app.py` + `streamlit_calendar`)
Renders the final schedule in two views:
- **List view**: tasks grouped by pet, with priority color badges
- **Calendar view**: weekly calendar with events color-coded by priority (red = non-negotiable, orange = high, yellow = medium, green = low)
- Conflict warnings are shown inline when overlapping tasks are detected

### 8. Human + Testing Layer
The user reviews the generated schedule and can edit any task (time, priority, duration, date range), mark tasks complete (which auto-schedules the next recurrence), or delete tasks. Conflicts are flagged with warning messages so the user can resolve them manually.

`tests/test_pawpal.py` uses `pytest` to validate the core domain logic: task completion, priority sorting, recurrence (`next_occurrence`), conflict detection, weekly schedule generation, and pet filtering. Test results are reviewed by the developer.

---

## Is This a Good Design?

**Overall: Yes — with some real gaps worth knowing.**

### What works well

- **Clear separation of layers.** Parsing, retrieval, classification, scheduling, and display are all separate concerns in separate files. This makes each piece testable and easy to change independently.
- **RAG pattern fits the problem.** Pulling only relevant rules from the knowledge base (rather than sending all 33 lines every time) keeps the LLM prompt focused and grounded. Groq's free tier (`llama3-8b-8192`) handles ambiguous phrasing that the old keyword classifier couldn't, while the retrieved context prevents hallucinated priorities. The fallback to rule-based logic means the app works even without a key.
- **Priority enforcement is explicit.** `non-negotiable` tasks always surface first. The classifier maps task types to priorities using real domain knowledge (medication and vet appointments outrank grooming and play), not arbitrary numbers.
- **Human review is built in.** The design does not treat the AI output as final. The user can inspect, edit, and override everything the classifier produces. Conflict warnings require human resolution rather than automatic dropping.
- **Testing covers the logic.** The test suite validates the scheduler's behavior on conflict detection, recurrence, and priority sorting — the rules that matter most for correctness.

### Real gaps in the current design

| Gap | Why it matters |
|---|---|
| **No persistence layer** | Session state is wiped on page refresh. Tasks cannot be saved between sessions. A database or file export would be needed for real use. |
| **Classifier has no confidence score** | When the input is vague, Groq returns a reason string but the UI does not show it to the user. Surfacing the reason ("classified as medication because: ...") would help users catch misclassifications. |
| **No feedback loop** | If a user edits a classifier output (e.g., changes priority from "medium" to "non-negotiable"), that correction is never used to improve future parsing. |
| **File upload is not implemented** | The original design mentioned text file upload; only text-area input currently exists. |
| **Multi-pet routing is fragile** | Pet name detection in the parser relies on checking if a known pet's name appears in the task line. A pet named "Max" would match any task line containing "max" (e.g., "max duration"). |
| **Tests don't cover the RAG layer** | `test_pawpal.py` tests domain logic but not `retrieve_context` or `classify_task`. A mistyped keyword in the classifier would not be caught by any test. |

### What would make it stronger

1. Add tests for `retrieve_context` and `classify_task` with known inputs and expected outputs.
2. Show a "parsed as: walk, high priority, 08:30" confirmation in the UI before saving, so users can catch misclassifications before they appear on the calendar.
3. Add a simple JSON export/import so schedules survive page refreshes.
