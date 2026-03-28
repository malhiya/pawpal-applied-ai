import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Task, Pet


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
