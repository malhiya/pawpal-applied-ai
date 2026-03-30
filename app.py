import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
available_minutes = st.number_input("Available minutes today", min_value=1, max_value=480, value=60)
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if "owners" not in st.session_state:
    st.session_state.owners = []

if st.button("Create Owner & Pet"):
    pet = Pet(pet_name, species, age=1)
    existing = next((o for o in st.session_state.owners if o.name == owner_name), None)
    if existing:
        existing.available_minutes = int(available_minutes)
        if not any(p.name == pet_name for p in existing.pets):
            existing.add_pet(pet)
    else:
        new_owner = Owner(owner_name, available_minutes=int(available_minutes))
        new_owner.add_pet(pet)
        st.session_state.owners.append(new_owner)

if st.session_state.owners:
    st.write("**Saved owners:**")
    for o in st.session_state.owners:
        pet_names = ", ".join(p.name for p in o.pets)
        st.write(f"- {o.name} ({o.available_minutes} min) — pets: {pet_names}")
else:
    st.info("No owners yet.")

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if not st.session_state.owners:
    st.info("Create an owner and pet first.")
else:
    selected_owner_name = st.selectbox("Owner", [o.name for o in st.session_state.owners])
    selected_owner = next(o for o in st.session_state.owners if o.name == selected_owner_name)

    if not selected_owner.pets:
        st.info(f"{selected_owner_name} has no pets yet.")
    else:
        selected_pet_name = st.selectbox("Pet", [p.name for p in selected_owner.pets])
        selected_pet = next(p for p in selected_owner.pets if p.name == selected_pet_name)

        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

        col4, col5, col6 = st.columns(3)
        with col4:
            frequency = st.selectbox("Frequency", ["daily", "weekly"])
        with col5:
            import datetime
            scheduled_time = st.time_input("Time", value=datetime.time(8, 0))
        with col6:
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            scheduled_day = st.selectbox("Day (weekly only)", days_of_week, disabled=(frequency == "daily"))

        if st.button("Add task"):
            new_task = Task(
                name=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category="general",
                frequency=frequency,
                scheduled_time=scheduled_time.strftime("%H:%M"),
                scheduled_day=scheduled_day,
            )
            selected_pet.add_task(new_task)

        if selected_pet.tasks:
            st.write("Current tasks:")
            for i, task in enumerate(selected_pet.tasks):
                col_check, col_status = st.columns([3, 1])
                with col_check:
                    checked = st.checkbox(
                        f"{task.name} ({task.priority}, {task.duration_minutes} min)",
                        value=task.is_complete,
                        key=f"task_{selected_owner_name}_{selected_pet_name}_{i}"
                    )
                    if checked and not task.is_complete:
                        task.mark_complete()
                with col_status:
                    if task.is_complete:
                        st.success("✅ Done")
        else:
            st.info("No tasks yet. Add one above.")

        st.divider()

        st.subheader("Build Schedule")
        st.caption(f"Schedule for {selected_owner_name} and {selected_pet_name}")

        if st.button("Generate schedule"):
            temp_owner = Owner(selected_owner.name, selected_owner.available_minutes)
            temp_owner.add_pet(selected_pet)
            scheduler = Scheduler(temp_owner)
            plan = scheduler.generate_plan()
            st.write(scheduler.explain_plan(selected_pet.tasks))

        st.divider()
        st.subheader("Weekly Schedule")
        if st.button("Generate weekly schedule"):
            temp_owner = Owner(selected_owner.name, selected_owner.available_minutes)
            temp_owner.add_pet(selected_pet)
            scheduler = Scheduler(temp_owner)
            weekly = scheduler.generate_weekly_schedule()

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

            # collect all unique times across the week, sorted
            all_times = sorted({task.scheduled_time for day_tasks in weekly.values() for task in day_tasks})

            if not all_times:
                st.info("No tasks scheduled yet.")
            else:
                # header row: Time | Mon | Tue | ...
                header_cols = st.columns([1] + [2] * 7)
                header_cols[0].markdown("**Time**")
                for i, day in enumerate(days):
                    header_cols[i + 1].markdown(f"**{day[:3]}**")

                st.divider()

                # one row per unique time slot
                for time_slot in all_times:
                    row_cols = st.columns([1] + [2] * 7)
                    row_cols[0].markdown(f"`{time_slot}`")
                    for i, day in enumerate(days):
                        tasks_at_time = [t for t in weekly[day] if t.scheduled_time == time_slot]
                        if tasks_at_time:
                            row_cols[i + 1].write("\n".join(t.name for t in tasks_at_time))
                        else:
                            row_cols[i + 1].caption("—")
