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
    # Pet has no direct link to Task in the UML, so tasks apply to all pets by default.
    # To make a task pet-specific (e.g. meds only for dogs), add: species: str | None = None
    # then filter in generate_plan: task.species is None or task.species == owner.pet.species


class Scheduler:
    def __init__(self, owner: Owner, tasks: list[Task]):
        self.owner = owner
        self.tasks: list[Task] = tasks
        # reset this at the start of each generate_plan call to avoid stale results
        self.skipped_tasks: list[Task] = []
        # store the last generated plan so explain_plan can reference it without re-running
        self.plan: list[Task] = []

    def generate_plan(self) -> list[Task]:
        """
        Filter, sort, and greedily select tasks that fit within
        owner.available_minutes. Stores unfit tasks in skipped_tasks.
        Returns the ordered list of selected tasks.

        Note: reset skipped_tasks and use a local 'remaining' counter —
        never mutate owner.available_minutes directly.
        """
        pass

    def explain_plan(self) -> str:
        """
        Returns a human-readable string explaining why each task was
        included or skipped.

        Note: depends on self.plan and self.skipped_tasks being populated.
        Call generate_plan() first, or guard with an early return if self.plan is empty.
        """
        pass

    def add_task(self, task: Task) -> None:
        """Add a task to the task list."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove a task from the task list.
        Raise ValueError if the task is not found."""
        pass

    def edit_task(self, old: Task, updated: Task) -> None:
        """Replace old task with updated task.
        Raise ValueError if old task is not found."""
        pass
