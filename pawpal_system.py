from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta


@dataclass
class Task:
    name: str
    duration_minutes: int
    priority: str       # "non-negotiable", "high", "medium", or "low"
    category: str       # e.g. "walk", "feeding", "meds", "grooming"
    frequency: str      # e.g. "daily", "weekly"
    scheduled_time: str = "08:00"  # 24-hour format, e.g. "08:00", "14:30"
    scheduled_day: str = "Monday"  # for weekly tasks: which day of the week
    is_complete: bool = False
    pet_name: str = ""       # set automatically when added to a pet via Pet.add_task
    scheduled_date: str = "" # ISO date string, e.g. "2026-03-29"; set on creation and next occurrences

    def mark_complete(self) -> None:
        """Mark this task as complete."""
        self.is_complete = True

    def next_occurrence(self) -> "Task":
        """Return a new incomplete copy of this task scheduled for its next occurrence.
        Daily tasks advance by 1 day; weekly tasks advance by 7 days."""
        if self.frequency == "daily":
            next_date = date.today() + timedelta(days=1)
        else:  # weekly
            next_date = date.today() + timedelta(weeks=1)
        return replace(self, is_complete=False, scheduled_date=next_date.isoformat(), pet_name="")


class Pet:
    def __init__(self, name: str, species: str, age: int):
        self.name = name
        self.species = species
        self.age = age
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        task.pet_name = self.name
        self.tasks.append(task)

    def complete_task(self, task: Task) -> Task:
        """Mark task complete and add a new instance scheduled for its next occurrence."""
        task.mark_complete()
        next_task = task.next_occurrence()
        self.add_task(next_task)  # sets pet_name automatically
        return next_task

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's task list, or raise ValueError if not found."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task.name}' not found.")
        self.tasks.remove(task)

    def edit_task(self, old: Task, updated: Task) -> None:
        """Replace old task with updated task, or raise ValueError if old task is not found."""
        if old not in self.tasks:
            raise ValueError(f"Task '{old.name}' not found.")
        index = self.tasks.index(old)
        self.tasks[index] = updated


class Owner:
    def __init__(self, name: str):
        self.name = name
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from the owner's pet list, or raise ValueError if not found."""
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
        """Build a priority-sorted task plan that fits within the owner's available time budget."""
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

        # sort by priority: non-negotiable first, then high, medium, low
        priority_order = {"non-negotiable": 0, "high": 1, "medium": 2, "low": 3}
        sorted_tasks = sorted(incomplete_tasks, key=lambda t: priority_order.get(t.priority, 4))
        # efficient one-liner: same as above, sorted() is already concise

        self.plan = sorted_tasks

        return self.plan

    def explain_plan(self, all_tasks: list) -> str:
        """Return a human-readable summary of which tasks were included or skipped and why."""
        if not self.plan and not self.skipped_tasks:
            return "No plan generated yet. Call generate_plan() first."

        explanation = ""

        explanation += "Tasks included in the plan:\n\n"
        for task in self.plan:
            index = all_tasks.index(task)
            explanation += f"  {index}. {task.name} ({task.priority} priority, {task.duration_minutes} min) — fits within time budget\n"

        if self.skipped_tasks:
            explanation += "\nTasks skipped:\n\n"
            for task in self.skipped_tasks:
                index = all_tasks.index(task)
                explanation += f"  {index}. {task.name} ({task.priority} priority, {task.duration_minutes} min) — not enough time remaining\n\n"

        explanation += "\nTasks are organized by priority (non-negotiable → high → medium → low), ensuring the most important care gets done first within the available time budget.\n"

        return explanation

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return a new list of tasks sorted by their scheduled_time attribute (ascending)."""
        return sorted(tasks, key=lambda t: t.scheduled_time)

    def filter_by_pet(self, tasks: list[Task], pet_name: str) -> list[Task]:
        """Return only tasks belonging to the named pet. Returns all tasks if pet_name is 'All Pets'."""
        if pet_name == "All Pets":
            return tasks
        return [task for task in tasks if task.pet_name == pet_name]

    def detect_conflicts(self, weekly: dict[str, list[Task]]) -> list[str]:
        """Return warning messages for any two tasks whose time ranges overlap on the same day."""
        warnings = []
        for day, tasks in weekly.items():
            for i, a in enumerate(tasks):
                start_a = datetime.strptime(a.scheduled_time, "%H:%M")
                end_a = start_a + timedelta(minutes=a.duration_minutes)
                for b in tasks[i + 1:]:
                    start_b = datetime.strptime(b.scheduled_time, "%H:%M")
                    end_b = start_b + timedelta(minutes=b.duration_minutes)
                    if start_a < end_b and start_b < end_a:
                        warnings.append(
                            f"{day}: '{a.name}' [{a.pet_name}] "
                            f"({a.scheduled_time}–{end_a.strftime('%H:%M')}) overlaps with "
                            f"'{b.name}' [{b.pet_name}] "
                            f"({b.scheduled_time}–{end_b.strftime('%H:%M')})"
                        )
        return warnings

    def generate_weekly_schedule(self, pet_name: str = "All Pets") -> dict[str, list[Task]]:
        """Return a dict mapping each day of the week to its list of tasks, sorted by scheduled_time.
        Only includes tasks that fit within the time budget (skipped tasks are excluded).
        Pass a pet_name to filter to a single pet, or 'All Pets' for the combined schedule."""
        if not self.plan:
            self.generate_plan()

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule: dict[str, list[Task]] = {day: [] for day in days}

        tasks_to_schedule = self.filter_by_pet(self.plan, pet_name)

        for task in tasks_to_schedule:
            if task.frequency == "daily":
                for day in days:
                    schedule[day].append(task)
            elif task.frequency == "weekly" and task.scheduled_day in schedule:
                schedule[task.scheduled_day].append(task)

        for day in days:
            schedule[day].sort(key=lambda t: t.scheduled_time)

        return schedule
