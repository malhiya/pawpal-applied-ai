# Model Card: PawPal+ Scheduler v1.1

---

## Model Name

**PawPal+ Scheduler v1.1**
*"Paws, Plans, and Priorities"*

---

## Goal / Task

PawPal+ Scheduler is a pet care task recommender that converts plain-English descriptions into a structured, prioritized, conflict-free weekly schedule. Given input like *"Give Luna her medication at 8am"* or *"Walk Max after breakfast"*, the system infers what kind of task it is, how urgent it is, how long it takes, and when to schedule it — then fits it into a weekly calendar alongside the pet owner's other responsibilities.

The core prediction tasks are:

- **Priority classification**: How important is this task? (non-negotiable → high → medium → low)
- **Category detection**: What type of care does this task represent? (medication, vet, feeding, walk, grooming, play, training)
- **Time inference**: When should this happen? (from explicit times like "at 8am" or cues like "after breakfast")
- **Duration estimation**: How long will it take?
- **Conflict detection**: Does this task overlap with another already on the schedule?

---

## Data Used

**Knowledge Base (`knowledge_base.md`)**
A 33-line domain rule file containing:
- Priority mappings: medication and vet = non-negotiable; walks and feeding = high; grooming = medium; play and training = low
- Duration defaults per category (e.g., medication = 5 min, walk = 30 min, vet = 60 min)
- Time-of-day defaults for natural language cues (e.g., "morning" = 08:00, "after breakfast" = 08:30, "evening" = 18:00)
- Scheduling rules: tasks cannot overlap, frequency is daily or weekly, date ranges have start and end

**Keyword taxonomy (hardcoded in `rag_helper.py`)**
Ten topic categories, each associated with a set of trigger keywords:
- Medication: med, meds, medication, pill, pills, dose, drops, supplement
- Vet: vet, veterinarian, appointment, checkup, clinic, doctor
- Feeding: feed, food, meal, breakfast, lunch, dinner, water, eat
- Walk: walk, walking, exercise, run, jog, outdoor, leash
- Grooming: groom, bath, bathe, brush, nail, trim, haircut
- Play: play, toy, fetch, enrichment, game
- Training: train, command, practice, lesson
- Time: morning, evening, night, afternoon, after, bedtime, lunchtime, am, pm
- Schedule: daily, weekly, next, every, Monday–Sunday
- Health: health, sick, ill, hurt, pain, emergency

**User-provided data (session-only, not persisted)**
- Owner name and pet profiles (name, species, age)
- Free-text task descriptions or structured form fields
- Manual edits (priority overrides, time adjustments, duration changes, date range modifications)

**Dataset size and limits**
There is no training dataset. All rules are handcrafted. Input is capped at 2,000 characters and 20 tasks per submission. Data lives only in Streamlit session state and is lost on page refresh.

**Limitations of the data**
The knowledge base reflects assumptions about "typical" pet care routines for dogs and cats in a Western household context. Species like reptiles, birds, or fish have no dedicated rules. The keyword vocabulary was chosen manually and does not cover synonyms or colloquialisms beyond what was anticipated during development.

---

## Algorithm Summary

PawPal+ uses a Retrieval-Augmented Generation (RAG) pipeline. Retrieval is keyword-based against a local knowledge base; classification is handled by **Llama 3 (8B) via the Groq API**.

**Step 1 — Retrieval**
Each free-text task line is tokenized. The system checks which keyword categories the tokens match and retrieves only the relevant lines from the knowledge base — not the entire file. For example, a task mentioning "medication" retrieves only the KB lines about medication priority, duration, and timing rules.

**Step 2 — LLM Classification (Groq / Llama 3)**
The retrieved KB lines and the original task string are sent to `llama3-8b-8192` via the Groq API. The model uses the retrieved rules as context to assign:
- **Priority**: non-negotiable, high, medium, or low — grounded in the retrieved KB lines
- **Category**: meds, vet, feeding, walk, grooming, play, training, or general
- **Reason**: a one-sentence explanation citing the rule that informed the decision

If the API call fails or no key is set, the pipeline falls back to the original deterministic keyword classifier silently.

**Step 2b — Deterministic parsing (unchanged)**
Dates, times, durations, and schedule frequency are still handled by regular expressions:
- **Duration**: extracted from phrases like "for 30 minutes"; otherwise the category default is used
- **Scheduled time**: extracted from patterns like "at 8am"; keyword cues like "morning" or "after breakfast" map to fixed times; if no time hint is given, the system finds the next available slot starting from a category-based default (grooming → 10:00, play → 15:00, training → 17:00, etc.)
- **Frequency and date range**: patterns like "from 04/28 to 05/05", "next Monday", or "every Saturday" are parsed by regex; unknown inputs default to daily recurrence for 30 days

**Step 3 — Conflict Detection**
Before a task is added to the schedule, the system checks whether its time window overlaps with any existing task on the same day. Overlap is determined by: `start_new < end_existing AND start_existing < end_new`. Conflicting tasks are not auto-resolved — the user is warned and must manually adjust the time.

**Step 4 — Priority Sorting**
All incomplete tasks are collected and sorted into priority tiers in order: non-negotiable → high → medium → low. Within a tier, tasks appear in the order they were entered. The weekly calendar then filters tasks by date range and frequency to show which tasks appear on each day.

There is no numeric score, no confidence value, and no probabilistic model. Every decision is deterministic and rule-based.

---

## Observed Behavior / Biases

**Keyword fragility**
The system performs well on clear, conventional phrasing ("Give Luna her medication at 8am") but silently falls back to defaults on ambiguous or informal input ("do Luna's morning thing" → general task, medium priority, 08:00). There is no warning when this happens; users may not realize their task was misclassified.

**Priority distribution skew**
The keyword taxonomy covers far more medication and vet-related terms than play or enrichment terms. Play and training tasks are consistently ranked lowest regardless of actual importance to the owner — for example, a dog with behavioral issues may need daily training sessions that are functionally higher priority than casual grooming, but the system cannot reflect that.

**No cross-species differentiation**
All species (dog, cat, other) use the same priority and duration defaults. A reptile's feeding schedule or a bird's enrichment needs have no dedicated rules and would be misclassified if entered.

**Assumed Western daily rhythm**
Time-of-day defaults (morning = 08:00, evening = 18:00, night = 21:00) assume a standard 9-to-5 lifestyle. Owners who work night shifts or have non-standard routines will need to manually override every inferred time.

**No feedback loop**
The system never learns from user corrections. If a user repeatedly overrides "walk" from high to non-negotiable because their dog is diabetic and needs structured exercise, the system will not adapt. The next task entered will still default to high.

---

## Evaluation Process

**Unit test suite (50+ tests across `tests/test_pawpal.py` and `tests/test_rag_helper.py`)**

Testing covered:
- Priority classification for all seven task categories and the unknown/fallback case
- Time inference for explicit times (8am, 9:30pm), keyword cues (morning, after breakfast), and no-hint defaults
- Duration defaults per category and explicit duration extraction
- Conflict detection between two tasks at the same time on the same day
- Multi-line input parsing, including blank line handling and the 20-task cap
- Task completion behavior, including daily recurrence scheduling
- Input validation, including the 2,000-character truncation guardrail
- RAG retrieval accuracy — verifying that "medication" retrieves medication KB lines and not unrelated rules

**Manual testing experiments**
During development, sample pet profiles were created (a dog owner managing walks, feeding, medication, and vet appointments) to verify:
- Conflict warnings appeared correctly when two tasks were scheduled at 08:00 on the same day
- Weekly tasks appeared only on their correct days
- The "all pets" mode correctly routed tasks containing a known pet name

**What was not measured**
No precision, recall, or accuracy metrics were computed. No A/B comparison was done against a baseline (e.g., a pure keyword matcher without RAG retrieval). No user study or real-world trial was conducted. Test coverage for date range parsing and edge cases (e.g., end date before start date, ambiguous pet-name-as-keyword conflicts) was incomplete.

---

## Intended Use and Non-Intended Use

**Intended use**
- Individual pet owners managing one or a small number of pets who want to organize care tasks into a weekly schedule
- Users who want a fast, private, no-account scheduling tool that runs entirely in their browser session
- Pet owners who have relatively standard care routines that map onto the supported categories (medication, vet, feeding, walk, grooming, play, training)

**Not intended for**
- Veterinary clinics or professional pet care businesses managing many animals simultaneously
- Emergency or medical decision-making — the system assigns "non-negotiable" as a scheduling priority, not a clinical urgency flag
- Species beyond dogs and cats, where defaults and priority rules may not apply
- Long-term record keeping — all data is lost on page refresh and there is no export or storage feature
- Users whose phrasing, language style, or daily rhythms fall outside the narrow keyword vocabulary and time defaults the system was built around

---

## Ideas for Improvement

**1. Improve prompt robustness for the Groq call**
The current prompt asks Llama 3 to return strict JSON, but the model occasionally wraps it in markdown fences or adds explanation text. A more defensive parsing strategy — or using Groq's JSON mode if available — would reduce edge-case failures and make the fallback trigger less often.

**2. Learn from user edits**
Every time a user overrides a priority, time, or duration that the system inferred, that correction is a labeled training signal. Storing these corrections (locally, not in a server) and using them to adjust the category-to-default mapping for that specific owner would make the system personalize over time without requiring any external model training.

**3. Expand species support and allow custom priority rules**
Add species-specific knowledge base entries for common exotic pets (reptiles, birds, fish) and expose a simple settings panel where owners can override the global priority mapping — for example, marking "walk" as non-negotiable for a diabetic dog, or promoting "training" to high for a dog in behavioral rehabilitation. This would eliminate the most common case where the system's defaults diverge from the owner's actual priorities.

---

## Reflections

The biggest limitation is how rigid the keyword classification is. If a user phrases something outside what I anticipated, the system silently falls back to defaults with no warning, and that kind of bias is hard to notice unless you are actively looking for it. The system also has no memory and no clinical knowledge, so someone could over-rely on it for medication reminders and not realize their data disappears on refresh. Making those limits more visible in the UI would help prevent that. What surprised me most during testing was how many times I had to manually run through different scenarios to find bugs. I would write a unit test, it would pass, and then I would actually use the app and immediately hit an edge case the test never covered. I believe there are still a few more that will come up the more the app gets used. Working with Claude Code was really helpful when thinking through logic bottlenecks or potential issues before building something new. For example, when I was considering making a task object store more than one pet, Claude pointed out that it was possible but would make things more complicated before the RAG component was even fully built. I decided to hold off and keep it simple for now. On the other side, Claude sometimes suggested more abstraction or error handling than the feature actually needed, and I had to push back to keep the code from growing beyond the scope of what I was trying to build.
