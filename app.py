import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler
from streamlit_calendar import calendar as st_calendar


@st.dialog("Task Details")
def show_task_details():
    ev = st.session_state.get("clicked_task", {})
    p  = ev.get("extendedProps", {})
    event_id = ev.get("id", "")
    is_done  = st.session_state.get(event_id, False)

    st.markdown(f"### {p.get('name', '—')}")
    st.write(f"**Pet:** {p.get('petName', '—')}")
    st.write(f"**Time:** {p.get('start', '—')} – {p.get('end', '—')} ({p.get('duration', '—')} min)")
    st.write(f"**Priority:** {p.get('priority', '—')}")
    st.write(f"**Status:** {'✅ Done' if is_done else 'Pending'}")

    if is_done:
        if st.button("Mark Incomplete", use_container_width=True):
            st.session_state[event_id] = False
            st.rerun()
    else:
        if st.button("Mark Complete", type="primary", use_container_width=True):
            st.session_state[event_id] = True
            st.rerun()

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

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
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if "owners" not in st.session_state:
    st.session_state.owners = []

if st.button("Create Owner & Pet"):
    pet = Pet(pet_name, species, age=1)
    existing = next((o for o in st.session_state.owners if o.name == owner_name), None)
    if existing:
        if not any(p.name == pet_name for p in existing.pets):
            existing.add_pet(pet)
    else:
        new_owner = Owner(owner_name)
        new_owner.add_pet(pet)
        st.session_state.owners.append(new_owner)

if st.session_state.owners:
    st.write("**Saved owners:**")
    for o in st.session_state.owners:
        pet_names = ", ".join(p.name for p in o.pets)
        st.write(f"- {o.name} — pets: {pet_names}")
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
            priority = st.selectbox("Priority", ["low", "medium", "high", "non-negotiable"], index=2)

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
            def task_window(task):
                start = datetime.datetime.strptime(task.scheduled_time, "%H:%M")
                end = start + datetime.timedelta(minutes=task.duration_minutes)
                return start, end

            all_existing = [t for pet in selected_owner.pets for t in pet.tasks]
            conflict = None
            new_start, new_end = task_window(new_task)
            for existing in all_existing:
                if existing.is_complete:
                    continue
                same_day = (
                    existing.frequency == "daily"
                    or new_task.frequency == "daily"
                    or existing.scheduled_day == new_task.scheduled_day
                )
                if not same_day:
                    continue
                ex_start, ex_end = task_window(existing)
                if new_start < ex_end and ex_start < new_end:
                    conflict = existing
                    break
            if conflict:
                ex_start, ex_end = task_window(conflict)
                st.error(
                    f"Task '{new_task.name}' was not added due to a scheduling conflict: "
                    f"'{conflict.name}' [{conflict.pet_name}] runs from "
                    f"{ex_start.strftime('%H:%M')} to {ex_end.strftime('%H:%M')}. "
                    f"Please choose a different time or adjust the duration."
                )
            else:
                selected_pet.add_task(new_task)

        if "editing_task_index" not in st.session_state:
            st.session_state.editing_task_index = None

        if selected_pet.tasks:
            st.write("Current tasks:")
            for i, task in enumerate(selected_pet.tasks):
                col_check, col_status, col_edit, col_delete = st.columns([3, 1, 1, 1])
                with col_check:
                    checked = st.checkbox(
                        f"{task.name} ({task.priority}, {task.duration_minutes} min)",
                        value=task.is_complete,
                        key=f"task_{selected_owner_name}_{selected_pet_name}_{i}"
                    )
                    if checked and not task.is_complete:
                        selected_pet.complete_task(task)
                with col_status:
                    if task.is_complete:
                        st.success("✅ Done")
                with col_edit:
                    if st.button("Edit", key=f"edit_{selected_owner_name}_{selected_pet_name}_{i}"):
                        st.session_state.editing_task_index = i
                with col_delete:
                    if st.button("Delete", key=f"delete_{selected_owner_name}_{selected_pet_name}_{i}"):
                        selected_pet.remove_task(task)
                        if st.session_state.editing_task_index == i:
                            st.session_state.editing_task_index = None
                        st.rerun()

            edit_i = st.session_state.editing_task_index
            if edit_i is not None and edit_i < len(selected_pet.tasks):
                task_to_edit = selected_pet.tasks[edit_i]
                st.markdown("**Edit task:**")
                with st.form(key="edit_task_form"):
                    new_name = st.text_input("Task title", value=task_to_edit.name)
                    new_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=task_to_edit.duration_minutes)
                    new_priority = st.selectbox("Priority", ["low", "medium", "high", "non-negotiable"], index=["low", "medium", "high", "non-negotiable"].index(task_to_edit.priority))
                    new_frequency = st.selectbox("Frequency", ["daily", "weekly"], index=["daily", "weekly"].index(task_to_edit.frequency))
                    new_time = st.time_input("Time", value=datetime.time(*map(int, task_to_edit.scheduled_time.split(":"))))
                    new_day = st.selectbox("Day (weekly only)", days_of_week, index=days_of_week.index(task_to_edit.scheduled_day), disabled=(new_frequency == "daily"))
                    col_save, col_cancel = st.columns(2)
                    save = col_save.form_submit_button("Save")
                    cancel = col_cancel.form_submit_button("Cancel")

                if save:
                    from dataclasses import replace as dc_replace
                    updated = dc_replace(
                        task_to_edit,
                        name=new_name,
                        duration_minutes=int(new_duration),
                        priority=new_priority,
                        frequency=new_frequency,
                        scheduled_time=new_time.strftime("%H:%M"),
                        scheduled_day=new_day,
                    )
                    selected_pet.edit_task(task_to_edit, updated)
                    st.session_state.editing_task_index = None
                    st.rerun()
                if cancel:
                    st.session_state.editing_task_index = None
                    st.rerun()
        else:
            st.info("No tasks yet. Add one above.")

        st.divider()

        st.subheader("Build Schedule")
        st.caption(f"Schedule for {selected_owner_name} — all pets")

        if st.button("Generate schedule"):
            scheduler = Scheduler(selected_owner)
            plan = scheduler.generate_plan()
            st.session_state["last_plan_scheduler"] = scheduler
            st.session_state["last_plan"] = plan
            all_tasks = [task for pet in selected_owner.pets for task in pet.tasks]
            st.write(scheduler.explain_plan(all_tasks))

        if "last_plan_scheduler" in st.session_state and st.session_state["last_plan"]:
            if st.button("Sort by Time"):
                sorted_tasks = st.session_state["last_plan_scheduler"].sort_by_time(st.session_state["last_plan"])
                st.markdown("**Tasks sorted by scheduled time:**")
                for task in sorted_tasks:
                    st.write(f"`{task.scheduled_time}` — {task.name} [{task.pet_name}] ({task.priority}, {task.duration_minutes} min)")

        st.divider()
        st.subheader("Weekly Planner")

        pet_filter_options = ["All Pets"] + [p.name for p in selected_owner.pets]
        selected_pet_filter = st.selectbox("Filter by pet", pet_filter_options, key="weekly_pet_filter")

        _time_options = [
            datetime.time(h, m).strftime("%I:%M %p").lstrip("0")
            for h in range(24) for m in (0, 30)
        ]
        _time_24 = [
            datetime.time(h, m).strftime("%H:%M")
            for h in range(24) for m in (0, 30)
        ]
        _display_to_24 = dict(zip(_time_options, _time_24))

        plan_col1, plan_col2, plan_col3 = st.columns(3)
        with plan_col1:
            start_display = st.selectbox("Start time", _time_options, index=12, key="plan_start")
        with plan_col2:
            end_display = st.selectbox("End time", _time_options, index=44, key="plan_end")
        with plan_col3:
            interval_label = st.selectbox("Interval", ["15 min", "30 min", "1 hour", "2 hours"], index=2, key="plan_interval")
        interval_map = {"15 min": 15, "30 min": 30, "1 hour": 60, "2 hours": 120}
        interval_minutes = interval_map[interval_label]

        if st.button("Generate weekly schedule"):
            scheduler = Scheduler(selected_owner)
            st.session_state["last_weekly_scheduler"] = scheduler

        if "last_weekly_scheduler" in st.session_state:
            weekly = st.session_state["last_weekly_scheduler"].generate_weekly_schedule(pet_name=selected_pet_filter)

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            today = datetime.date.today()
            day_to_date = {
                day: (today + datetime.timedelta(days=(i - today.weekday()) % 7)).isoformat()
                for i, day in enumerate(days)
            }

            priority_colors = {
                "non-negotiable": {"bg": "#ffaaaa", "border": "#cc3333"},
                "high":           {"bg": "#ffcc88", "border": "#cc6600"},
                "medium":         {"bg": "#fff099", "border": "#ccaa00"},
                "low":            {"bg": "#aaddaa", "border": "#337733"},
            }

            events = []
            for day, tasks in weekly.items():
                for t in tasks:
                    done_key = f"done_{t.name}_{t.pet_name}_{day}_{t.scheduled_time}"
                    is_done = st.session_state.get(done_key, False)
                    colors = priority_colors.get(t.priority, {"bg": "#cccccc", "border": "#888888"})
                    end_time_obj = (
                        datetime.datetime.strptime(t.scheduled_time, "%H:%M")
                        + datetime.timedelta(minutes=t.duration_minutes)
                    )
                    end_str = end_time_obj.strftime('%H:%M')
                    events.append({
                        "id": done_key,
                        "title": f"✅ {t.name} [{t.pet_name}]" if is_done else f"{t.name} [{t.pet_name}]",
                        "start": f"{day_to_date[day]}T{t.scheduled_time}:00",
                        "end":   f"{day_to_date[day]}T{end_str}:00",
                        "backgroundColor": "#d0d0d0" if is_done else colors["bg"],
                        "borderColor":     "#999999" if is_done else colors["border"],
                        "textColor":       "#888888" if is_done else "#333333",
                        "extendedProps": {
                            "name":     t.name,
                            "petName":  t.pet_name,
                            "start":    t.scheduled_time,
                            "end":      end_str,
                            "duration": t.duration_minutes,
                            "priority": t.priority,
                        },
                    })

            plan_start_24 = _display_to_24[start_display]
            plan_end_24   = _display_to_24[end_display]
            slot_duration = f"{interval_minutes // 60:02d}:{interval_minutes % 60:02d}:00"

            cal_options = {
                "initialView": "timeGridWeek",
                "initialDate": today.isoformat(),
                "firstDay": (today.weekday() + 1) % 7,
                "slotMinTime": f"{plan_start_24}:00",
                "slotMaxTime": f"{plan_end_24}:00",
                "slotDuration": slot_duration,
                # "slotEventOverlap": False, 
                "headerToolbar": {
                    "left":   "prev,next today",
                    "center": "title",
                    "right":  "timeGridWeek,timeGridDay",
                },
                "height": 900,
                "slotMinHeight": 50,
                "eventMinHeight": 40,
                "expandRows": True,
                "nowIndicator": True,
                "allDaySlot": False,
            }

            conflicts = st.session_state["last_weekly_scheduler"].detect_conflicts(weekly)
            if conflicts:
                with st.expander(f"⚠️ {len(conflicts)} scheduling conflict(s) detected — tasks overlap in time", expanded=True):
                    for msg in conflicts:
                        st.warning(msg)

            if not events:
                st.info("No tasks scheduled yet.")
            else:
                st.caption("Click an event to view details.")
                st.markdown(
                    """
                    <style>
                    iframe[title="streamlit_calendar.calendar"] {
                        width: 100% !important;
                        min-width: 100% !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                result = st_calendar(events=events, options=cal_options, key="weekly_cal")
                if result and result.get("eventClick"):
                    st.session_state["clicked_task"] = result["eventClick"]["event"]
                    show_task_details()

