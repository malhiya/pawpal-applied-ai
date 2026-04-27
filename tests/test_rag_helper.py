import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from rag_helper import (
    parse_input,
    retrieve_context,
    classify_task,
    build_schedule,
    parse_tasks_with_rag,
    validate_raw_input,
    find_lines_missing_pet_name,
    _clean_task_name,
    _determine_priority,
    _determine_category,
    _parse_scheduled_time,
    _determine_schedule,
    load_knowledge_base,
    _MAX_INPUT_CHARS,
    _MAX_TASK_LINES,
)


# ── parse_input ───────────────────────────────────────────────────────────────

def test_parse_input_splits_multiline():
    text = "Walk Buddy\nFeed Max\nGive meds"
    assert parse_input(text) == ["Walk Buddy", "Feed Max", "Give meds"]


def test_parse_input_skips_blank_lines():
    text = "Walk Buddy\n\n  \nFeed Max"
    assert parse_input(text) == ["Walk Buddy", "Feed Max"]


def test_parse_input_single_line():
    assert parse_input("Give meds") == ["Give meds"]


def test_parse_input_empty_string():
    assert parse_input("") == []


# ── _clean_task_name ──────────────────────────────────────────────────────────

def test_clean_task_name_strips_time():
    assert _clean_task_name("walk at 8am") == "Walk"


def test_clean_task_name_strips_daily():
    assert _clean_task_name("feed every day") == "Feed"


def test_clean_task_name_strips_morning():
    result = _clean_task_name("walk in the morning")
    assert result == "Walk"


def test_clean_task_name_strips_next_weekday():
    result = _clean_task_name("vet appointment next monday")
    assert result == "Vet appointment"


def test_clean_task_name_preserves_core_action():
    result = _clean_task_name("give medication at 9pm daily")
    assert "medication" in result.lower() or "give" in result.lower()


def test_clean_task_name_capitalises_first_letter():
    result = _clean_task_name("brush teeth")
    assert result[0].isupper()


# ── _determine_category ───────────────────────────────────────────────────────

def test_determine_category_walk():
    tokens = {"walk", "buddy"}
    assert _determine_category(tokens) == "walk"


def test_determine_category_meds():
    tokens = {"give", "medication"}
    assert _determine_category(tokens) == "meds"


def test_determine_category_feeding():
    tokens = {"feed", "dinner"}
    assert _determine_category(tokens) == "feeding"


def test_determine_category_grooming():
    tokens = {"brush", "groom"}
    assert _determine_category(tokens) == "grooming"


def test_determine_category_vet():
    tokens = {"vet", "appointment"}
    assert _determine_category(tokens) == "vet"


def test_determine_category_play():
    tokens = {"play", "fetch"}
    assert _determine_category(tokens) == "play"


def test_determine_category_training():
    tokens = {"train", "command"}
    assert _determine_category(tokens) == "training"


def test_determine_category_unknown_defaults_to_general():
    tokens = {"something", "random"}
    assert _determine_category(tokens) == "general"


# ── _determine_priority ───────────────────────────────────────────────────────

def test_priority_medication_is_non_negotiable():
    tokens = {"give", "medication"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "non-negotiable"


def test_priority_vet_is_non_negotiable():
    tokens = {"vet", "appointment"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "non-negotiable"


def test_priority_walk_is_high():
    tokens = {"walk", "buddy"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "high"


def test_priority_feeding_is_high():
    tokens = {"feed", "max"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "high"


def test_priority_grooming_is_medium():
    tokens = {"groom", "brush"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "medium"


def test_priority_play_is_low():
    tokens = {"play", "fetch"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "low"


def test_priority_unknown_defaults_to_medium():
    tokens = {"something", "random"}
    priority, _ = _determine_priority(tokens, [])
    assert priority == "medium"


# ── _parse_scheduled_time ─────────────────────────────────────────────────────

def test_parse_time_explicit_am():
    assert _parse_scheduled_time("walk at 8am") == "08:00"


def test_parse_time_explicit_pm():
    assert _parse_scheduled_time("give meds at 9pm") == "21:00"


def test_parse_time_with_minutes():
    assert _parse_scheduled_time("feed at 7:30am") == "07:30"


def test_parse_time_morning_keyword():
    assert _parse_scheduled_time("walk in the morning") == "08:00"


def test_parse_time_evening_keyword():
    assert _parse_scheduled_time("walk in the evening") == "18:00"


def test_parse_time_after_breakfast():
    assert _parse_scheduled_time("feed after breakfast") == "08:30"


def test_parse_time_after_dinner():
    assert _parse_scheduled_time("walk after dinner") == "18:30"


def test_parse_time_night_keyword():
    assert _parse_scheduled_time("meds at night") == "21:00"


def test_parse_time_no_hint_defaults_to_0800():
    assert _parse_scheduled_time("walk Buddy") == "08:00"


def test_parse_time_noon():
    assert _parse_scheduled_time("meds at 12pm") == "12:00"


# ── retrieve_context ──────────────────────────────────────────────────────────

def test_retrieve_context_returns_relevant_lines():
    kb = load_knowledge_base()
    results = retrieve_context("give medication at 9pm", kb)
    assert any("medication" in r.lower() or "med" in r.lower() for r in results)


def test_retrieve_context_walk_returns_walk_rules():
    kb = load_knowledge_base()
    results = retrieve_context("walk Buddy", kb)
    assert any("walk" in r.lower() for r in results)


def test_retrieve_context_unrelated_input_returns_fewer_lines():
    kb = load_knowledge_base()
    results_walk = retrieve_context("walk the dog", kb)
    results_other = retrieve_context("xyzzy frobnicate", kb)
    assert len(results_walk) > len(results_other)


# ── classify_task ─────────────────────────────────────────────────────────────

def test_classify_task_walk():
    result = classify_task("walk Buddy at 8am daily", [])
    assert result["category"] == "walk"
    assert result["priority"] == "high"
    assert result["scheduled_time"] == "08:00"
    assert result["frequency"] == "daily"


def test_classify_task_medication_non_negotiable():
    result = classify_task("give medication at 9pm", [])
    assert result["priority"] == "non-negotiable"
    assert result["category"] == "meds"
    assert result["scheduled_time"] == "21:00"


def test_classify_task_vet_appointment():
    result = classify_task("vet appointment next monday", [])
    assert result["category"] == "vet"
    assert result["priority"] == "non-negotiable"
    assert result["frequency"] == "weekly"


def test_classify_task_returns_expected_keys():
    result = classify_task("feed Max in the morning", [])
    required_keys = {"task", "priority", "reason", "duration_minutes",
                     "category", "frequency", "scheduled_time",
                     "scheduled_day", "start_date", "end_date"}
    assert required_keys.issubset(result.keys())


def test_classify_task_duration_defaults():
    assert classify_task("walk Buddy", [])["duration_minutes"] == 30
    assert classify_task("give medication", [])["duration_minutes"] == 5
    assert classify_task("feed Max", [])["duration_minutes"] == 10
    assert classify_task("vet appointment", [])["duration_minutes"] == 60


# ── build_schedule ────────────────────────────────────────────────────────────

def test_build_schedule_returns_task_objects():
    from pawpal_system import Task
    classified = [
        {
            "task": "Walk",
            "priority": "high",
            "reason": "",
            "duration_minutes": 30,
            "category": "walk",
            "frequency": "daily",
            "scheduled_time": "08:00",
            "scheduled_day": "Monday",
            "start_date": "2026-04-26",
            "end_date": "2026-05-26",
        }
    ]
    tasks = build_schedule(classified)
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)
    assert tasks[0].name == "Walk"


# ── parse_tasks_with_rag (full pipeline) ─────────────────────────────────────

def test_full_pipeline_single_task():
    tasks, _ = parse_tasks_with_rag("walk Buddy at 8am", pet_name="Buddy")
    assert len(tasks) == 1
    assert tasks[0].category == "walk"
    assert tasks[0].scheduled_time == "08:00"


def test_full_pipeline_multiple_tasks():
    raw = "walk Buddy at 8am\ngive medication at 9pm\nfeed Max in the morning"
    tasks, _ = parse_tasks_with_rag(raw, pet_name="Buddy")
    assert len(tasks) == 3


def test_full_pipeline_priority_ordering():
    raw = "play fetch\ngive medication at 9pm\nwalk Buddy"
    tasks, _ = parse_tasks_with_rag(raw, pet_name="Buddy")
    categories = [t.category for t in tasks]
    assert "meds" in categories
    assert "walk" in categories
    assert "play" in categories


def test_full_pipeline_pet_detection_in_all_pets_mode():
    raw = "walk Buddy\nfeed Max"
    tasks, _ = parse_tasks_with_rag(raw, pet_name="Buddy",
                                     pet_names=["Buddy", "Max"])
    detected = {t.name: t.pet_name for t in tasks}
    assert any(v == "Buddy" for v in detected.values())
    assert any(v == "Max" for v in detected.values())


def test_full_pipeline_empty_input_returns_empty_list():
    tasks, _ = parse_tasks_with_rag("", pet_name="Buddy")
    assert tasks == []


# ── validate_raw_input ────────────────────────────────────────────────────────

def test_validate_raw_input_passes_normal_input():
    text = "walk Buddy at 8am\ngive medication at 9pm"
    result, warnings = validate_raw_input(text)
    assert result == text
    assert warnings == []


def test_validate_raw_input_truncates_long_input():
    long_text = "walk Buddy\n" * 300          # well over 2000 chars
    result, warnings = validate_raw_input(long_text)
    assert len(result) <= _MAX_INPUT_CHARS
    assert len(warnings) >= 1
    assert any("truncated" in w.lower() for w in warnings)


def test_validate_raw_input_caps_task_lines():
    many_lines = "\n".join(f"walk Buddy {i}" for i in range(_MAX_TASK_LINES + 5))
    result, warnings = validate_raw_input(many_lines)
    kept = [l for l in result.splitlines() if l.strip()]
    assert len(kept) == _MAX_TASK_LINES
    assert len(warnings) == 1
    assert str(_MAX_TASK_LINES) in warnings[0]


def test_validate_raw_input_empty_string():
    result, warnings = validate_raw_input("")
    assert result == ""
    assert warnings == []


# ── find_lines_missing_pet_name ───────────────────────────────────────────────

def test_find_lines_missing_pet_name_all_present():
    lines = ["walk Buddy at 8am", "give Max his medication"]
    assert find_lines_missing_pet_name(lines, ["Buddy", "Max"]) == []


def test_find_lines_missing_pet_name_some_missing():
    lines = ["walk Buddy at 8am", "give medication at 9pm"]
    missing = find_lines_missing_pet_name(lines, ["Buddy", "Max"])
    assert missing == ["give medication at 9pm"]


def test_find_lines_missing_pet_name_all_missing():
    lines = ["walk in the morning", "give medication at 9pm"]
    missing = find_lines_missing_pet_name(lines, ["Buddy", "Max"])
    assert missing == lines


def test_find_lines_missing_pet_name_case_insensitive():
    lines = ["Walk BUDDY at 8am"]
    assert find_lines_missing_pet_name(lines, ["Buddy"]) == []


def test_find_lines_missing_pet_name_partial_word_not_matched():
    # "Max" inside "Maximum" should not count
    lines = ["Maximum effort walk"]
    assert find_lines_missing_pet_name(lines, ["Max"]) == ["Maximum effort walk"]


def test_find_lines_missing_pet_name_empty_lines():
    assert find_lines_missing_pet_name([], ["Buddy"]) == []


# ─────────────────────────────────────────────────────────────────────────────

def test_full_pipeline_warns_when_input_exceeds_line_cap():
    many_lines = "\n".join(f"walk Buddy {i}" for i in range(_MAX_TASK_LINES + 5))
    tasks, warnings = parse_tasks_with_rag(many_lines, pet_name="Buddy")
    assert len(tasks) == _MAX_TASK_LINES
    assert any(str(_MAX_TASK_LINES) in w for w in warnings)
