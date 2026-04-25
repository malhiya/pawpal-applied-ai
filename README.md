# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Features

- **Priority-based scheduling** — tasks are sorted high → medium → low and greedily selected to fit within the owner's available time budget
- **Plan explanation** — after generating a plan, the app explains why each task was included or skipped (priority + time fit)
- **Daily recurrence** — completing a task automatically schedules its next occurrence one day later
- **Weekly recurrence** — weekly tasks are pinned to a specific day and appear only on that day in the weekly view
- **Weekly schedule view** — generates a full Mon–Sun schedule mapping each day to its sorted task list
- **Sort by time** — any task list can be sorted by `scheduled_time` in ascending order
- **Filter by pet** — narrow the schedule to a single pet or view all pets combined
- **Conflict detection** — flags any two tasks under the same owner that share the same start time on the same day

## Smarter Scheduling

Additonal features are added for a more natural and cleaner task scheduling. Weekly schedule output allows for recurring tasks to show. Filtering a schedule by a Pet allows a user to see the schedule of an individual pet. Tasks can also be sorted by time. And task conflictions are detected for any pet under the same owner for tasks with the same starting time. 

## Getting started

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest tests/test_pawpal.py -v
```

The tests cover:

- **Task completion** — marking a task complete updates its `is_complete` status
- **Pet task list** — adding a task increases the pet's task count
- **Sorting** — `sort_by_time` returns tasks in ascending chronological order
- **Recurrence** — completing a daily task creates a new task scheduled for the next day
- **Conflict detection** — `Scheduler.detect_conflicts` flags two tasks sharing the same time slot on the same day
- **Zero time budget** — `generate_plan` skips all tasks and populates `skipped_tasks` when `available_minutes` is 0
- **Double completion** — calling `complete_task` twice on the same task appends two future copies
- **`next_occurrence` pet name** — `next_occurrence()` resets `pet_name` to `""`, requiring the caller to re-assign it via `add_task`

### Confidence level

**4/5** — Core scheduling behaviors (sorting, priority, conflict detection, recurrence) work correctly. However, two real bugs were found during testing: `complete_task` has no guard against being called twice, and `next_occurrence` silently drops the pet name. Additional silent failure modes exist for invalid frequency values and unknown scheduled days. Coverage gaps remain in multi-pet scenarios and the UI layer.

## Demo

<a href="weekly_schedule.png" target="_blank"><img src='weekly_schedule.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="build_schedule.png" target="_blank"><img src='build_schedule.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="time_sort.png" target="_blank"><img src='time_sort.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="tasks.png" target="_blank"><img src='tasks.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="owners.png" target="_blank"><img src='owners.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>
