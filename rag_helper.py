"""
Lightweight rule-based RAG pipeline for PawPal+.

Pipeline:
  parse_input          -> split raw text into individual task lines
  load_knowledge_base  -> load KB as a list of rule lines
  retrieve_context     -> keyword-match each line against the KB (retrieval step)
  classify_task        -> rule-based classification using ONLY retrieved lines
  build_schedule       -> construct Task dataclasses from classified dicts
  parse_tasks_with_rag -> orchestrates the full pipeline
"""

import os
import re
import datetime
from pawpal_system import Task


_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "medication": ["medication", "med", "meds", "medicine", "pill", "pills",
                   "dose", "drops", "supplement", "treatment", "drug"],
    "vet":        ["vet", "veterinarian", "appointment", "check-up", "checkup",
                   "clinic", "doctor"],
    "feeding":    ["feed", "feeding", "food", "meal", "breakfast", "dinner",
                   "lunch", "water", "eat", "eating"],
    "walk":       ["walk", "walking", "walks", "exercise", "run", "jog",
                   "outdoor", "leash"],
    "grooming":   ["groom", "grooming", "bath", "bathe", "brush", "brushing",
                   "nail", "trim", "haircut"],
    "play":       ["play", "playtime", "toy", "fetch", "enrichment", "game"],
    "training":   ["train", "training", "command", "practice", "lesson"],
    "time":       ["morning", "evening", "night", "afternoon", "after",
                   "bedtime", "lunchtime", "am", "pm"],
    "schedule":   ["daily", "weekly", "next", "every",
                   "monday", "tuesday", "wednesday", "thursday",
                   "friday", "saturday", "sunday"],
    "health":     ["health", "sick", "ill", "hurt", "pain", "emergency"],
}

_DAYS_OF_WEEK = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]

_DEFAULT_DURATIONS: dict[str, int] = {
    "meds":     5,
    "feeding":  10,
    "walk":     30,
    "grooming": 20,
    "vet":      60,
    "play":     20,
    "training": 15,
    "general":  20,
}

# Patterns stripped from the raw input when building a clean task name
_MAX_INPUT_CHARS = 2000
_MAX_TASK_LINES  = 20

_CLEANUP_PATTERNS = [
    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",          # "at 8am", "at 8:30 pm"
    r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bfrom\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\s+to\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",  # "from 5/01 to 5/30"
    r"\bafter\s+breakfast\b",
    r"\bafter\s+dinner\b",
    r"\bafter\s+lunch\b",
    r"\bin\s+the\s+morning\b",
    r"\bin\s+the\s+evening\b",
    r"\bin\s+the\s+afternoon\b",
    r"\bat\s+night\b",
    r"\bat\s+bedtime\b",
    r"\bat\s+lunchtime\b",
    r"\bevery\s+day\b",
    r"\bevery\s+week\b",
    r"\bdaily\b",
    r"\bweekly\b",
]


# ── Step 1 ───────────────────────────────────────────────────────────────────

def load_knowledge_base() -> list[str]:
    """Load the knowledge base as individual rule lines, skipping blank lines."""
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.md")
    with open(kb_path, "r") as f:
        return [line.strip() for line in f if line.strip()]


# ── Step 2 ───────────────────────────────────────────────────────────────────

def parse_input(text: str) -> list[str]:
    """Split multi-line user input into individual task strings."""
    return [line.strip() for line in text.splitlines() if line.strip()]


# ── Step 3 ───────────────────────────────────────────────────────────────────

def retrieve_context(line: str, knowledge_base: list[str]) -> list[str]:
    """
    Retrieval step: return only the KB lines relevant to this task line.

    1. Tokenise the input line into lowercase words.
    2. Find which topic groups those tokens belong to.
    3. Return KB lines that contain any keyword from a matched topic.

    The full knowledge base is never passed forward — only the retrieved slice.
    """
    tokens = set(re.findall(r"\b\w+\b", line.lower()))

    matched_topics: set[str] = set()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in tokens for kw in keywords):
            matched_topics.add(topic)

    retrieved: list[str] = []
    for kb_line in knowledge_base:
        kb_lower = kb_line.lower()
        for topic in matched_topics:
            if any(kw in kb_lower for kw in _TOPIC_KEYWORDS[topic]):
                retrieved.append(kb_line)
                break

    return retrieved


# ── Step 4 helpers ────────────────────────────────────────────────────────────

def _clean_task_name(line: str) -> str:
    """
    Strip scheduling details (times, day references, frequency words) from
    the raw input string, leaving just the action description.
    Falls back to the original line if cleanup produces an empty string.
    """
    name = line
    for pattern in _CLEANUP_PATTERNS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s{2,}", " ", name).strip(" ,.;:")
    if name:
        return name[0].upper() + name[1:]
    return line.strip()


def _determine_priority(tokens: set[str], retrieved_context: list[str]) -> tuple[str, str]:
    """
    Determine priority from retrieved KB lines first, then keyword fallback.
    Returns (priority, reason_string).
    """
    non_neg = _TOPIC_KEYWORDS["medication"] + _TOPIC_KEYWORDS["vet"] + _TOPIC_KEYWORDS["health"]
    high    = _TOPIC_KEYWORDS["walk"] + _TOPIC_KEYWORDS["feeding"]
    medium  = _TOPIC_KEYWORDS["grooming"]
    low     = _TOPIC_KEYWORDS["play"] + _TOPIC_KEYWORDS["training"]

    for ctx_line in retrieved_context:
        ctx_lower = ctx_line.lower()
        if "non-negotiable" in ctx_lower and any(kw in tokens for kw in non_neg):
            return "non-negotiable", ctx_line
        if "high priority" in ctx_lower and any(kw in tokens for kw in high):
            return "high", ctx_line
        if "medium priority" in ctx_lower and any(kw in tokens for kw in medium):
            return "medium", ctx_line
        if "low priority" in ctx_lower and any(kw in tokens for kw in low):
            return "low", ctx_line

    # Keyword fallback when no KB line gave a direct signal
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["medication"]):
        return "non-negotiable", "Medication tasks are non-negotiable"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["vet"]):
        return "non-negotiable", "Vet appointments are non-negotiable"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["walk"]):
        return "high", "Dog walks are high priority"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["feeding"]):
        return "high", "Feeding tasks are high priority"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["grooming"]):
        return "medium", "Grooming tasks are medium priority"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["play"]):
        return "low", "Playtime is low priority"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["training"]):
        return "low", "Training sessions are low priority"
    return "medium", "No specific rule matched; defaulting to medium"


def _determine_category(tokens: set[str]) -> str:
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["medication"]):
        return "meds"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["vet"]):
        return "vet"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["feeding"]):
        return "feeding"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["walk"]):
        return "walk"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["grooming"]):
        return "grooming"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["play"]):
        return "play"
    if any(kw in tokens for kw in _TOPIC_KEYWORDS["training"]):
        return "training"
    return "general"


def _parse_scheduled_time(line: str) -> str:
    """Extract or infer a 24-hour HH:MM time from the task string."""
    match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", line, re.IGNORECASE)
    if match:
        hour   = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = (match.group(3) or "").lower()
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    tokens = set(re.findall(r"\b\w+\b", line.lower()))
    if "after" in tokens and "breakfast" in tokens:
        return "08:30"
    if "after" in tokens and "dinner" in tokens:
        return "18:30"
    if "morning" in tokens:
        return "08:00"
    if "afternoon" in tokens:
        return "14:00"
    if "evening" in tokens:
        return "18:00"
    if "night" in tokens or "bedtime" in tokens:
        return "21:00"
    if "lunchtime" in tokens or "lunch" in tokens:
        return "12:00"
    return "08:00"


def _parse_date_str(date_str: str, today: datetime.date) -> datetime.date:
    """Parse 'MM/DD' or 'MM/DD/YYYY' or 'MM/DD/YY' into a date. Assumes current year if omitted."""
    parts = date_str.strip().split("/")
    month, day = int(parts[0]), int(parts[1])
    if len(parts) == 3:
        year = int(parts[2])
        if year < 100:
            year += 2000
    else:
        year = today.year
    return datetime.date(year, month, day)


def _determine_schedule(line: str, tokens: set[str]) -> tuple[str, str, str, str]:
    """
    Returns (frequency, start_date, end_date, scheduled_day).
    Handles explicit date ranges, 'next [weekday]', and defaults to daily recurring.
    """
    today = datetime.date.today()

    # Explicit date range: "from 5/01 to 5/30" or "from 5/01/2026 to 5/30/2026"
    date_range = re.search(
        r"\bfrom\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+to\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
        line, re.IGNORECASE,
    )
    if date_range:
        try:
            start = _parse_date_str(date_range.group(1), today)
            end   = _parse_date_str(date_range.group(2), today)
            return "daily", start.isoformat(), end.isoformat(), today.strftime("%A")
        except (ValueError, IndexError):
            pass

    # "next [weekday]" — single-day one-time event
    for day_name in _DAYS_OF_WEEK:
        if re.search(rf"\bnext\s+{day_name}\b", line, re.IGNORECASE):
            days_ahead = ((_DAYS_OF_WEEK.index(day_name)) - today.weekday() + 7) % 7 or 7
            event_date = (today + datetime.timedelta(days=days_ahead)).isoformat()
            return "weekly", event_date, event_date, day_name.capitalize()

    end_30 = (today + datetime.timedelta(days=30)).isoformat()

    if "weekly" in tokens or any(kw in tokens for kw in _TOPIC_KEYWORDS["grooming"]):
        return "weekly", today.isoformat(), end_30, today.strftime("%A")

    return "daily", today.isoformat(), end_30, today.strftime("%A")


# ── Step 4 ───────────────────────────────────────────────────────────────────

def classify_task(line: str, retrieved_context: list[str]) -> dict:
    """
    Rule-based classification using ONLY the retrieved KB lines.
    No external APIs — fully deterministic.
    """
    tokens = set(re.findall(r"\b\w+\b", line.lower()))

    priority, reason             = _determine_priority(tokens, retrieved_context)
    category                     = _determine_category(tokens)
    duration                     = _DEFAULT_DURATIONS.get(category, 20)
    scheduled_time               = _parse_scheduled_time(line)
    frequency, start, end, s_day = _determine_schedule(line, tokens)

    return {
        "task":             _clean_task_name(line),
        "priority":         priority,
        "reason":           reason,
        "duration_minutes": duration,
        "category":         category,
        "frequency":        frequency,
        "scheduled_time":   scheduled_time,
        "scheduled_day":    s_day,
        "start_date":       start,
        "end_date":         end,
    }


# ── Step 5 ───────────────────────────────────────────────────────────────────

def build_schedule(classified_tasks: list[dict]) -> list[Task]:
    """Construct Task dataclasses from classified task dicts."""
    return [
        Task(
            name=td["task"],
            duration_minutes=td["duration_minutes"],
            priority=td["priority"],
            category=td["category"],
            frequency=td["frequency"],
            scheduled_time=td["scheduled_time"],
            scheduled_day=td["scheduled_day"],
            start_date=td["start_date"],
            end_date=td["end_date"],
            pet_name=td.get("detected_pet", ""),
        )
        for td in classified_tasks
    ]


# ── Input guardrails ──────────────────────────────────────────────────────────

def find_lines_missing_pet_name(lines: list[str], pet_names: list[str]) -> list[str]:
    """
    Return every line that contains none of the known pet names.
    Used in All Pets mode to catch ambiguous input before the pipeline runs.
    """
    return [
        line for line in lines
        if not any(
            re.search(rf"\b{re.escape(name.lower())}\b", line.lower())
            for name in pet_names
        )
    ]


def validate_raw_input(text: str) -> tuple[str, list[str]]:
    """
    Cap input size before it enters the pipeline.
    Returns (sanitized_text, warnings) so callers can surface what was trimmed.
    """
    warnings: list[str] = []

    if len(text) > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]
        warnings.append(
            f"Input was too long and has been truncated to {_MAX_INPUT_CHARS} characters. "
            "Please split large batches into multiple submissions."
        )

    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) > _MAX_TASK_LINES:
        lines = lines[:_MAX_TASK_LINES]
        warnings.append(
            f"Only the first {_MAX_TASK_LINES} tasks were processed. "
            "Please submit remaining tasks separately."
        )
        text = "\n".join(lines)

    return text, warnings


# ── Orchestrator ──────────────────────────────────────────────────────────────

def parse_tasks_with_rag(
    raw_input: str,
    pet_name: str,
    pet_names: list[str] | None = None,
) -> tuple[list[Task], list[str]]:
    """
    Full RAG pipeline:
      1. validate_raw_input   — cap input length and line count (guardrail)
      2. load_knowledge_base  — load KB rule lines from disk
      3. parse_input          — split text into individual task lines
      4. retrieve_context     — keyword-match each line against the KB
      5. classify_task        — rule-based classification using retrieved lines only
      6. build_schedule       — assemble Task dataclasses

    Returns (tasks, warnings). Warnings are user-facing messages about input that
    was trimmed or corrected by the guardrail.

    When pet_names is provided (All Pets mode), each task line is scanned for a
    matching pet name and tagged with detected_pet so the caller can route it to
    the right pet.
    """
    raw_input, warnings = validate_raw_input(raw_input)

    kb         = load_knowledge_base()
    task_lines = parse_input(raw_input)

    classified = []
    for line in task_lines:
        result = classify_task(line, retrieve_context(line, kb))
        if pet_names:
            line_lower = line.lower()
            result["detected_pet"] = next(
                (name for name in pet_names
                 if re.search(rf"\b{re.escape(name.lower())}\b", line_lower)),
                None,
            )
        classified.append(result)

    return build_schedule(classified), warnings
