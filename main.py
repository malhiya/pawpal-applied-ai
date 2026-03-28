from pawpal_system import Task, Pet, Owner, Scheduler

# Create owner
owner = Owner(name="Alex", available_minutes=50)

# Create pets
buddy = Pet(name="Buddy", species="Dog", age=3)
whiskers = Pet(name="Whiskers", species="Cat", age=5)

# Add tasks to Buddy (dog)
buddy.add_task(Task(name="Morning Walk", duration_minutes=30, priority="high", category="walk", frequency="daily"))
buddy.add_task(Task(name="Breakfast Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily"))
buddy.add_task(Task(name="Flea Medicine", duration_minutes=5, priority="medium", category="meds", frequency="weekly"))

# Add tasks to Whiskers (cat)
whiskers.add_task(Task(name="Dinner Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily"))
whiskers.add_task(Task(name="Brush Coat", duration_minutes=15, priority="low", category="grooming", frequency="weekly"))

# Register pets with owner
owner.add_pet(buddy)
owner.add_pet(whiskers)

# Generate schedule
scheduler = Scheduler(owner)
scheduler.generate_plan()

# Build a flat indexed list of all tasks across all pets
all_tasks = []
for pet in owner.pets:
    for task in pet.tasks:
        all_tasks.append(task)

# Print Today's Schedule
print("=" * 40)
print("        TODAY'S SCHEDULE")
print("=" * 40)
print(f"Owner : {owner.name}")
print(f"Budget: {owner.available_minutes} minutes\n")

for pet in owner.pets:
    print(f"[{pet.name} the {pet.species}]")
    for task in pet.tasks:
        status = "[done]" if task.is_complete else "[ ]"
        print(f"  {status}  {task.name} — {task.duration_minutes} min ({task.priority} priority)")
    print()

print("-" * 40)
print(scheduler.explain_plan(all_tasks))

# Build a map from task id to its pet for easy lookup
task_to_pet = {}
for pet in owner.pets:
    for task in pet.tasks:
        task_to_pet[id(task)] = pet

# Loop until all plan tasks are done or user skips
while not all(task.is_complete for task in scheduler.plan):
    print("\nEnter a task number to mark it as complete (or press Enter to skip): ", end="")
    user_input = input()

    if user_input.strip() == "":
        break

    task_index = int(user_input)
    selected_task = all_tasks[task_index]
    selected_task.mark_complete()
    print(f"\n'{selected_task.name}' marked as complete.")

    # Reprint the same plan with updated statuses (no regeneration)
    print("\n" + "=" * 40)
    print("     UPDATED SCHEDULE")
    print("=" * 40)

    for task in scheduler.plan:
        index = all_tasks.index(task)
        pet = task_to_pet[id(task)]
        status = "[done]" if task.is_complete else "[ ]"
        print(f"  {index}. {status} {pet.name}: {task.name} — {task.duration_minutes} min ({task.priority} priority)")

if all(task.is_complete for task in scheduler.plan):
    print("\nAll tasks are done for today!")
