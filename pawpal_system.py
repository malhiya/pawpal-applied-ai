from dataclasses import dataclass


@dataclass
class Pet:
    name: str
    species: str
    age: int


@dataclass
class Owner:
    name: str
    available_minutes: int
    pet: Pet


@dataclass
class Task:
    name: str
    duration_minutes: int
    priority: str   # "high", "medium", or "low"
    category: str   # e.g. "walk", "feeding", "meds", "grooming"


class Scheduler:
    def __init__(self, owner: Owner, tasks: list[Task]):
        self.owner = owner
        self.tasks: list[Task] = tasks
        self.skipped_tasks: list[Task] = []

    def generate_plan(self) -> list[Task]:
        """
        Filter, sort, and greedily select tasks that fit within
        owner.available_minutes. Stores unfit tasks in skipped_tasks.
        Returns the ordered list of selected tasks.
        """
        pass

    def explain_plan(self) -> str:
        """
        Returns a human-readable string explaining why each task was
        included or skipped.
        """
        pass

    def add_task(self, task: Task) -> None:
        """Add a task to the task list."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove a task from the task list."""
        pass

    def edit_task(self, old: Task, updated: Task) -> None:
        """Replace old task with updated task."""
        pass
