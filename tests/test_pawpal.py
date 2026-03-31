import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


def test_mark_complete_changes_status():
    task = Task(name="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily")
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="dog", age=3)
    assert len(pet.tasks) == 0
    task = Task(name="Feed", duration_minutes=10, priority="medium", category="feeding", frequency="daily")
    pet.add_task(task)
    assert len(pet.tasks) == 1

def test_sort_by_time_returns_chronological_order():
    owner = Owner(name="Alex", available_minutes=120)
    scheduler = Scheduler(owner)

    tasks = [
        Task(name="Evening Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", scheduled_time="18:00"),
        Task(name="Morning Feed", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="07:00"),
        Task(name="Noon Meds", duration_minutes=5, priority="medium", category="meds", frequency="daily", scheduled_time="12:00"),
    ]

    sorted_tasks = scheduler.sort_by_time(tasks)

    assert sorted_tasks[0].scheduled_time == "07:00"
    assert sorted_tasks[1].scheduled_time == "12:00"
    assert sorted_tasks[2].scheduled_time == "18:00"


def test_complete_daily_task_creates_next_day_occurrence():
    pet = Pet(name="Buddy", species="dog", age=3)
    task = Task(name="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily")
    pet.add_task(task)

    pet.complete_task(task)

    expected_date = (date.today() + timedelta(days=1)).isoformat()
    new_task = pet.tasks[-1]

    assert task.is_complete is True
    assert new_task.is_complete is False
    assert new_task.scheduled_date == expected_date
    assert new_task.pet_name == "Buddy"


def test_detect_conflicts_flags_duplicate_times():
    owner = Owner(name="Alex", available_minutes=120)
    scheduler = Scheduler(owner)

    task1 = Task(name="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", scheduled_time="08:00", pet_name="Buddy")
    task2 = Task(name="Feed", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="08:00", pet_name="Max")
    task3 = Task(name="Meds", duration_minutes=5, priority="medium", category="meds", frequency="daily", scheduled_time="09:00", pet_name="Buddy")

    weekly = {"Monday": [task1, task2, task3]}
    warnings = scheduler.detect_conflicts(weekly)

    assert len(warnings) == 1
    assert "08:00" in warnings[0]
    assert "Walk" in warnings[0]
    assert "Feed" in warnings[0]


##Extra Tests##
def test_generate_plan_zero_available_minutes():
    """Scheduler should skip all tasks and return an empty plan when the owner
    has zero available minutes, placing every task in skipped_tasks instead."""
    owner = Owner(name="Alex", available_minutes=0)
    pet = Pet(name="Buddy", species="dog", age=3)
    pet.add_task(Task(name="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan()

    assert plan == []
    assert len(scheduler.skipped_tasks) == 1


def test_complete_task_twice_adds_two_future_copies():
    """Calling complete_task twice on the same task should append two new future
    task instances, because the method does not guard against already-complete tasks."""
    pet = Pet(name="Buddy", species="dog", age=3)
    task = Task(name="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily")
    pet.add_task(task)

    pet.complete_task(task)
    pet.complete_task(task)  # called again on the already-complete original

    # original + 2 new occurrences
    assert len(pet.tasks) == 3


def test_next_occurrence_resets_pet_name_to_empty():
    """next_occurrence() is a public method on Task that returns a copy scheduled
    for the next date. It resets pet_name to '' — callers are responsible for
    re-assigning it. This test pins that contract so regressions are caught early."""
    task = Task(
        name="Walk",
        duration_minutes=30,
        priority="high",
        category="walk",
        frequency="daily",
        pet_name="Buddy",
    )

    next_task = task.next_occurrence()

    assert next_task.pet_name == ""
