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
from dotenv import load_dotenv
from pawpal_system import Task

load_dotenv()


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
                   "friday", "saturday", "sunday",
                   "mondays", "tuesdays", "wednesdays", "thursdays",
                   "fridays", "saturdays", "sundays"],
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

_DEFAULT_TIMES: dict[str, str] = {
    "meds":     "08:00",
    "feeding":  "07:30",
    "walk":     "09:00",
    "vet":      "10:00",
    "grooming": "10:00",
    "play":     "15:00",
    "training": "17:00",
    "general":  "09:00",
}

# Patterns stripped from the raw input when building a clean task name
_MAX_INPUT_CHARS = 2000
_MAX_TASK_LINES  = 20

_CLEANUP_PATTERNS = [
    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",          # "at 8am", "at 8:30 pm"
    r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bfrom\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\s+to\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",  # "from 5/01 to 5/30"
    r"\bon\s+(?:(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+)?\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",  # "on Wednesday 4/30"
    r"\bfor\s+\d+\s+(?:minutes?|mins?|hours?|hrs?)\b",     # "for 30 minutes"
    r"\bafter\s+breakfast\b",
    r"\bafter\s+dinner\b",
    r"\bafter\s+lunch\b",
    r"\bin\s+the\s+morning\b",
    r"\bin\s+the\s+evening\b",
    r"\bin\s+the\s+afternoon\b",
    r"\bat\s+night\b",
    r"\bat\s+bedtime\b",
    r"\bat\s+lunchtime\b",
    r"\bevery\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\b",  # "every Saturday"
    r"\bevery\s+day\b",
    r"\bevery\s+week\b",
    r"\bdaily\b",
    r"\bweekly\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\b",  # standalone day names
]

# Verb phrases stripped from the *start* of the name after other cleanup
_FILLER_PREFIXES = [
    r"^has\s+(?:an?\s+)?",
    r"^needs?\s+(?:to\s+)?",
    r"^should\s+(?:get\s+(?:an?\s+)?)?",
    r"^gets?\s+(?:an?\s+)?",
    r"^will\s+(?:have\s+(?:an?\s+)?|get\s+(?:an?\s+)?)?",
    r"^is\s+getting\s+(?:an?\s+)?",
    r"^(?:his|her|their|its)\s+",
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

def _clean_task_name(line: str, pet_names: list[str] | None = None) -> str:
    """
    Strip pet names, scheduling details, day references, and leading filler
    verb phrases from the raw input, leaving just the action description.
    Falls back to the original line if cleanup produces an empty string.
    """
    name = line
    for pn in (pet_names or []):
        name = re.sub(rf"\b{re.escape(pn)}\b", "", name, flags=re.IGNORECASE)
    for pattern in _CLEANUP_PATTERNS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s{2,}", " ", name).strip(" ,.;:")
    for pattern in _FILLER_PREFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip(" ,.;:")
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


def _parse_scheduled_time(line: str, category: str = "general") -> tuple[str, bool]:
    """
    Extract or infer a 24-hour HH:MM time from the task string.
    Returns (time_str, was_explicit). was_explicit is False only when
    no time hint at all was found and a category default was used.
    """
    match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", line, re.IGNORECASE)
    if match:
        hour   = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = (match.group(3) or "").lower()
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}", True

    tokens = set(re.findall(r"\b\w+\b", line.lower()))
    if "after" in tokens and "breakfast" in tokens:
        return "08:30", True
    if "after" in tokens and "dinner" in tokens:
        return "18:30", True
    if "morning" in tokens:
        return "08:00", True
    if "afternoon" in tokens:
        return "14:00", True
    if "evening" in tokens:
        return "18:00", True
    if "night" in tokens or "bedtime" in tokens:
        return "21:00", True
    if "lunchtime" in tokens or "lunch" in tokens:
        return "12:00", True
    return _DEFAULT_TIMES.get(category, "09:00"), False


def _parse_duration(line: str, default: int) -> int:
    """Extract an explicit duration from phrases like 'for 30 minutes' or 'for 1 hour'."""
    match = re.search(r"\bfor\s+(\d+)\s+(?:minutes?|mins?)\b", line, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"\bfor\s+(\d+)\s+(?:hours?|hrs?)\b", line, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 60
    return default


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


def _extract_weekday(line: str) -> str | None:
    """
    Return the first weekday name mentioned in the line that isn't part of
    an 'on [weekday] MM/DD' single-day pattern (which would be a one-time date,
    not a recurring day-of-week). Matches both singular and plural (e.g. "Tuesdays").
    """
    # Strip "on [weekday] MM/DD" so those don't count as recurring weekday references
    scrubbed = re.sub(
        r"\bon\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
        "", line, flags=re.IGNORECASE,
    )
    for day_name in _DAYS_OF_WEEK:
        if re.search(rf"\b{day_name}s?\b", scrubbed, re.IGNORECASE):
            return day_name.capitalize()
    return None


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
            # If a specific weekday is also mentioned, treat as weekly on that day
            weekday = _extract_weekday(line)
            if weekday:
                return "weekly", start.isoformat(), end.isoformat(), weekday
            return "daily", start.isoformat(), end.isoformat(), today.strftime("%A")
        except (ValueError, IndexError):
            pass

    # "on [weekday] MM/DD" or "on MM/DD" — single-day event on a specific date
    single_day_match = re.search(
        r"\bon\s+(?:(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+)?(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
        line, re.IGNORECASE,
    )
    if single_day_match:
        try:
            event_date = _parse_date_str(single_day_match.group(1), today)
            return "weekly", event_date.isoformat(), event_date.isoformat(), event_date.strftime("%A")
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
        weekday = _extract_weekday(line)
        return "weekly", today.isoformat(), end_30, weekday or today.strftime("%A")

    return "daily", today.isoformat(), end_30, today.strftime("%A")


# ── Slot-finding helpers ──────────────────────────────────────────────────────

def _has_time_conflict(
    time_str: str,
    duration: int,
    frequency: str,
    scheduled_day: str,
    start_date: str,
    end_date: str,
    others: list,
) -> bool:
    """Return True if the given time window overlaps any task in others (Task or dict)."""
    t_start = datetime.datetime.strptime(time_str, "%H:%M")
    t_end   = t_start + datetime.timedelta(minutes=duration)
    try:
        sd = datetime.date.fromisoformat(start_date)
        ed = datetime.date.fromisoformat(end_date)
    except (ValueError, TypeError):
        sd = ed = datetime.date.today()

    for other in others:
        if isinstance(other, dict):
            o_time, o_dur  = other.get("scheduled_time", "08:00"), other.get("duration_minutes", 20)
            o_freq, o_day  = other.get("frequency", "daily"), other.get("scheduled_day", "Monday")
            o_start, o_end = other.get("start_date", ""), other.get("end_date", "")
        else:
            if getattr(other, "is_complete", False):
                continue
            o_time, o_dur  = other.scheduled_time, other.duration_minutes
            o_freq, o_day  = other.frequency, other.scheduled_day
            o_start, o_end = other.start_date, other.end_date

        try:
            os_d = datetime.date.fromisoformat(o_start) if o_start else datetime.date.today()
            oe_d = datetime.date.fromisoformat(o_end)   if o_end   else os_d
        except ValueError:
            os_d = oe_d = datetime.date.today()

        if not (sd <= oe_d and os_d <= ed):
            continue
        same_day = (
            frequency == "daily" or o_freq == "daily"
            or scheduled_day == o_day
        )
        if not same_day:
            continue
        o_start_dt = datetime.datetime.strptime(o_time, "%H:%M")
        o_end_dt   = o_start_dt + datetime.timedelta(minutes=o_dur)
        if t_start < o_end_dt and o_start_dt < t_end:
            return True
    return False


def _find_available_time(
    start_time: str,
    duration: int,
    frequency: str,
    scheduled_day: str,
    start_date: str,
    end_date: str,
    all_tasks: list,
) -> str:
    """
    Starting from start_time, try 30-minute increments until a conflict-free
    slot is found before 22:00. Returns the original time if none is found.
    """
    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    candidate = to_minutes(start_time)
    while candidate + duration <= 22 * 60:
        t = f"{candidate // 60:02d}:{candidate % 60:02d}"
        if not _has_time_conflict(t, duration, frequency, scheduled_day, start_date, end_date, all_tasks):
            return t
        candidate += 30
    return start_time


# ── Step 4 ───────────────────────────────────────────────────────────────────

def _groq_classify(line: str, retrieved_context: list[str]) -> dict | None:
    """
    Ask Groq (Llama) to classify priority, category, and reason using the
    retrieved KB lines as context. Returns a dict or None if the call fails.
    """
    import json
    import os
    try:
        from groq import Groq
    except ImportError:
        return None

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    context_block = "\n".join(retrieved_context) if retrieved_context else "No specific rules found."
    prompt = (
        "You are a pet care scheduling assistant.\n"
        "Use ONLY the rules below to classify the task.\n\n"
        f"Rules:\n{context_block}\n\n"
        f"Task: {line}\n\n"
        "Reply with valid JSON only — no markdown, no explanation:\n"
        '{"priority": "non-negotiable|high|medium|low", '
        '"category": "meds|vet|feeding|walk|grooming|play|training|general", '
        '"reason": "one sentence citing the rule"}'
    )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        text = response.choices[0].message.content.strip()
        text = text.lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(text)
    except Exception:
        return None


def classify_task(line: str, retrieved_context: list[str], pet_names: list[str] | None = None) -> dict:
    """
    Classify a task using Groq/Llama with retrieved KB lines as context (RAG).
    Falls back to rule-based logic if the API call fails or key is missing.
    """
    tokens = set(re.findall(r"\b\w+\b", line.lower()))

    groq_result = _groq_classify(line, retrieved_context)
    if groq_result:
        priority = groq_result.get("priority", "medium")
        category = groq_result.get("category", _determine_category(tokens))
        reason   = groq_result.get("reason", "Classified by Groq")
    else:
        priority, reason = _determine_priority(tokens, retrieved_context)
        category         = _determine_category(tokens)

    duration                     = _parse_duration(line, _DEFAULT_DURATIONS.get(category, 20))
    scheduled_time, time_explicit = _parse_scheduled_time(line, category)
    frequency, start, end, s_day = _determine_schedule(line, tokens)

    return {
        "task":             _clean_task_name(line, pet_names),
        "priority":         priority,
        "reason":           reason,
        "duration_minutes": duration,
        "category":         category,
        "frequency":        frequency,
        "scheduled_time":   scheduled_time,
        "scheduled_day":    s_day,
        "start_date":       start,
        "end_date":         end,
        "_time_explicit":   time_explicit,
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
    existing_tasks: list | None = None,
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

    single = [pet_name] if (pet_name and pet_name != "All Pets") else None
    names_to_strip = pet_names if pet_names else single

    all_known = list(existing_tasks or [])
    classified = []
    for line in task_lines:
        result = classify_task(line, retrieve_context(line, kb), pet_names=names_to_strip)
        if not result.pop("_time_explicit"):
            result["scheduled_time"] = _find_available_time(
                result["scheduled_time"],
                result["duration_minutes"],
                result["frequency"],
                result["scheduled_day"],
                result["start_date"],
                result["end_date"],
                all_known + classified,
            )
        if pet_names:
            line_lower = line.lower()
            result["detected_pet"] = next(
                (name for name in pet_names
                 if re.search(rf"\b{re.escape(name.lower())}\b", line_lower)),
                None,
            )
        classified.append(result)

    return build_schedule(classified), warnings
