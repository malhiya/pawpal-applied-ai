from dataclasses import dataclass, field


@dataclass
class Task:
    name: str
    duration_minutes: int
    priority: str       # "high", "medium", or "low"
    category: str       # e.g. "walk", "feeding", "meds", "grooming"
    frequency: str      # e.g. "daily", "weekly"
    is_complete: bool = False
    # Note: is_complete is never auto-reset — for recurring tasks (e.g. daily walks),
    # you'll need to reset this between planning sessions manually.


class Pet:
    def __init__(self, name: str, species: str, age: int):
        self.name = name
        self.species = species
        self.age = age
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's task list.
        Raise ValueError if the task is not found."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task.name}' not found.")
        self.tasks.remove(task)

    def edit_task(self, old: Task, updated: Task) -> None:
        """Replace old task with updated task.
        Raise ValueError if old task is not found.
        Note: if called after generate_plan, self.plan becomes stale — regenerate the plan."""
        if old not in self.tasks:
            raise ValueError(f"Task '{old.name}' not found.")
        index = self.tasks.index(old)
        self.tasks[index] = updated


class Owner:
    def __init__(self, name: str, available_minutes: int):
        self.name = name
        # used by Scheduler as the time budget — never mutate directly inside generate_plan
        self.available_minutes = available_minutes
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from the owner's pet list.
        Raise ValueError if the pet is not found.
        Note: tasks from this pet may still exist in Scheduler.plan — regenerate the plan after removal."""
        if pet not in self.pets:
            raise ValueError(f"Pet '{pet.name}' not found.")
        self.pets.remove(pet)


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner
        # reset at the start of each generate_plan call to avoid stale results
        self.skipped_tasks: list[Task] = []
        # stores the last generated plan so explain_plan can reference it
        self.plan: list[Task] = []

    def generate_plan(self) -> list[Task]:
        """
        Aggregate tasks from all owner.pets, filter out completed tasks,
        sort by priority (high → medium → low), then greedily select tasks
        that fit within owner.available_minutes.
        Stores tasks that didn't fit in skipped_tasks.
        Returns the ordered list of selected tasks.

        Note: reset self.plan and self.skipped_tasks at the start to avoid stale data from prior calls.
        Use a local 'remaining' counter — never mutate owner.available_minutes directly.
        """
        self.plan = []
        self.skipped_tasks = []

        # collect all tasks from every pet
        all_tasks = []
        for pet in self.owner.pets:
            for task in pet.tasks:
                all_tasks.append(task)
        # efficient one-liner: all_tasks = [task for pet in self.owner.pets for task in pet.tasks]

        # filter out already completed tasks
        incomplete_tasks = []
        for task in all_tasks:
            if not task.is_complete:
                incomplete_tasks.append(task)

        # sort by priority: high first, then medium, then low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_tasks = sorted(incomplete_tasks, key=lambda t: priority_order.get(t.priority, 3))
        # efficient one-liner: same as above, sorted() is already concise

        # greedily add tasks that fit within the time budget
        remaining = self.owner.available_minutes
        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                self.plan.append(task)
                remaining -= task.duration_minutes
            else:
                self.skipped_tasks.append(task)

        return self.plan

    def explain_plan(self) -> str:
        """
        Returns a human-readable string explaining why each task was
        included or excluded.

        Note: depends on self.plan and self.skipped_tasks being populated.
        Call generate_plan() first, or guard with an early return if self.plan is empty.
        """
        if not self.plan and not self.skipped_tasks:
            return "No plan generated yet. Call generate_plan() first."

        explanation = ""

        explanation += "Tasks included in the plan:\n"
        for task in self.plan:
            explanation += f"  - {task.name} ({task.priority} priority, {task.duration_minutes} min) — fits within time budget\n"

        if self.skipped_tasks:
            explanation += "\nTasks skipped:\n"
            for task in self.skipped_tasks:
                explanation += f"  - {task.name} ({task.priority} priority, {task.duration_minutes} min) — not enough time remaining\n"

        return explanation
