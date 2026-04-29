import datetime
import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler
from streamlit_calendar import calendar as st_calendar


@st.dialog("Edit Task")
def show_edit_task_dialog():
    import datetime as _dt
    pet = st.session_state.get("editing_pet")
    edit_i = st.session_state.get("editing_task_index")
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if pet is None or edit_i is None or edit_i >= len(pet.tasks):
        st.warning("No task selected.")
        return

    task_to_edit = pet.tasks[edit_i]
    new_name = st.text_input("Task title", value=task_to_edit.name)
    new_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=task_to_edit.duration_minutes)
    new_priority = st.selectbox("Priority", ["low", "medium", "high", "non-negotiable"], index=["low", "medium", "high", "non-negotiable"].index(task_to_edit.priority))
    edit_single_day = st.checkbox("Single-day appointment", value=(task_to_edit.start_date == task_to_edit.end_date and bool(task_to_edit.start_date)))
    new_frequency = st.selectbox("Frequency", ["daily", "weekly"], index=["daily", "weekly"].index(task_to_edit.frequency), disabled=edit_single_day)
    _edit_time_opts = [
        _dt.time(h, m).strftime("%I:%M %p").lstrip("0")
        for h in range(24) for m in (0, 30)
    ]
    _edit_time_24 = [
        _dt.time(h, m).strftime("%H:%M")
        for h in range(24) for m in (0, 30)
    ]
    _edit_display_to_24 = dict(zip(_edit_time_opts, _edit_time_24))
    _cur_h, _cur_m = map(int, task_to_edit.scheduled_time.split(":"))
    _cur_time_rounded = _dt.time(_cur_h, 30 if _cur_m >= 30 else 0).strftime("%H:%M")
    _edit_default_idx = _edit_time_24.index(_cur_time_rounded) if _cur_time_rounded in _edit_time_24 else 16
    _edit_time_display = st.selectbox("Time", _edit_time_opts, index=_edit_default_idx)
    new_time_str = _edit_display_to_24[_edit_time_display]
    new_day = st.selectbox("Day (weekly only)", days_of_week, index=days_of_week.index(task_to_edit.scheduled_day), disabled=(edit_single_day or new_frequency == "daily"))
    edit_col1, edit_col2 = st.columns(2)
    with edit_col1:
        default_start = _dt.date.fromisoformat(task_to_edit.start_date) if task_to_edit.start_date else _dt.date.today()
        new_start_date = st.date_input("Start date", value=default_start, format="MM/DD/YYYY", key="edit_start_date")
    with edit_col2:
        if edit_single_day:
            new_end_date = new_start_date
            st.date_input("End date", value=new_start_date, format="MM/DD/YYYY", disabled=True, key="edit_end_date_disabled")
        else:
            default_end = _dt.date.fromisoformat(task_to_edit.end_date) if task_to_edit.end_date else default_start + _dt.timedelta(days=7)
            new_end_date = st.date_input("End date", value=default_end, format="MM/DD/YYYY", key="edit_end_date")

    col_save, col_cancel = st.columns(2)
    save = col_save.button("Save", type="primary", use_container_width=True)
    cancel = col_cancel.button("Cancel", use_container_width=True)

    if save:
        if not new_name.strip():
            st.error("Task name cannot be empty.")
            return
        if new_end_date < new_start_date:
            st.error("End date cannot be before start date.")
            return
        from dataclasses import replace as dc_replace
        import datetime as _dt2
        updated = dc_replace(
            task_to_edit,
            name=new_name.strip(),
            duration_minutes=int(new_duration),
            priority=new_priority,
            frequency=new_frequency,
            scheduled_time=new_time_str,
            scheduled_day=new_day,
            start_date=new_start_date.isoformat(),
            end_date=new_end_date.isoformat(),
        )

        def _window(t):
            s = _dt2.datetime.strptime(t.scheduled_time, "%H:%M")
            return s, s + _dt2.timedelta(minutes=t.duration_minutes)

        def _dates_overlap(t1, t2):
            if not t1.start_date or not t2.start_date:
                return True
            s1 = _dt2.date.fromisoformat(t1.start_date)
            e1 = _dt2.date.fromisoformat(t1.end_date) if t1.end_date else s1
            s2 = _dt2.date.fromisoformat(t2.start_date)
            e2 = _dt2.date.fromisoformat(t2.end_date) if t2.end_date else s2
            return s1 <= e2 and s2 <= e1

        owner = st.session_state.get("editing_owner")
        all_tasks = [t for p in owner.pets for t in p.tasks] if owner else pet.tasks
        conflict = None
        u_start, u_end = _window(updated)
        for existing in all_tasks:
            if existing is task_to_edit or existing.is_complete:
                continue
            if not _dates_overlap(updated, existing):
                continue
            same_day = (
                existing.frequency == "daily"
                or updated.frequency == "daily"
                or existing.scheduled_day == updated.scheduled_day
            )
            if not same_day:
                continue
            ex_start, ex_end = _window(existing)
            if u_start < ex_end and ex_start < u_end:
                conflict = existing
                break

        if conflict:
            ex_start, ex_end = _window(conflict)
            st.warning(
                f"Time conflict with '{conflict.name}' ({conflict.pet_name}) "
                f"which runs {ex_start.strftime('%H:%M')}–{ex_end.strftime('%H:%M')}. "
                f"Please choose a different time or adjust the duration."
            )
        else:
            pet.edit_task(task_to_edit, updated)
            st.session_state.editing_task_index = None
            st.session_state.editing_pet = None
            st.session_state.editing_owner = None
            st.rerun()
    if cancel:
        st.session_state.editing_task_index = None
        st.session_state.editing_pet = None
        st.session_state.editing_owner = None
        st.rerun()


@st.dialog("Task Details")
def show_task_details():
    ev = st.session_state.get("clicked_task", {})
    p  = ev.get("extendedProps", {})
    event_id = ev.get("id", "")
    is_done  = st.session_state.get(event_id, False)

    st.markdown(f"### {p.get('name', '—')}")
    st.write(f"**Pet:** {p.get('petName', '—')}")
    st.write(f"**Date:** {p.get('date', '—')}")
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

@st.dialog("Edit Owner & Pets")
def show_edit_owner_dialog():
    owner = st.session_state.get("editing_owner_for_names")
    if owner is None:
        st.warning("No owner selected.")
        return

    new_owner_name = st.text_input("Owner name", value=owner.name, key="edit_owner_name_input")

    new_pet_names = []
    new_pet_species = []
    if owner.pets:
        st.markdown("**Pets:**")
        for i, pet in enumerate(owner.pets):
            col_name, col_species = st.columns([2, 1])
            with col_name:
                new_pet_names.append(
                    st.text_input(f"Pet {i + 1} name", value=pet.name, key=f"edit_pet_name_{i}")
                )
            with col_species:
                species_opts = ["dog", "cat"]
                cur_idx = species_opts.index(pet.species) if pet.species in species_opts else 2
                new_pet_species.append(
                    st.selectbox(f"Species", species_opts, index=cur_idx, key=f"edit_pet_species_{i}")
                )

    col_save, col_cancel = st.columns(2)
    save = col_save.button("Save", type="primary", use_container_width=True)
    cancel = col_cancel.button("Cancel", use_container_width=True)

    if save:
        if not new_owner_name.strip():
            st.error("Owner name cannot be empty.")
            return
        for name in new_pet_names:
            if not name.strip():
                st.error("Pet name cannot be empty.")
                return

        owner.name = new_owner_name.strip()
        for i, pet in enumerate(owner.pets):
            new_name = new_pet_names[i].strip()
            if pet.name != new_name:
                for task in pet.tasks:
                    task.pet_name = new_name
                pet.name = new_name
            pet.species = new_pet_species[i]

        st.session_state.editing_owner_for_names = None
        st.rerun()

    if cancel:
        st.session_state.editing_owner_for_names = None
        st.rerun()


@st.dialog("Confirm Delete")
def show_delete_confirmation():
    pet  = st.session_state.get("deleting_pet")
    task = st.session_state.get("deleting_task")
    idx  = st.session_state.get("deleting_task_index")

    if pet is None or task is None:
        st.warning("No task selected.")
        return

    st.warning(
        f"**'{task.name}'** is marked **non-negotiable**. "
        "Deleting it may cause a missed medication or critical care task. "
        "Are you sure you want to remove it?"
    )
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Delete anyway", type="primary", use_container_width=True):
            pet.remove_task(task)
            if st.session_state.get("editing_task_index") == idx:
                st.session_state.editing_task_index = None
            st.session_state.deleting_pet = None
            st.session_state.deleting_task = None
            st.session_state.deleting_task_index = None
            st.rerun()
    with col_no:
        if st.button("Cancel", use_container_width=True):
            st.session_state.deleting_pet = None
            st.session_state.deleting_task = None
            st.session_state.deleting_task_index = None
            st.rerun()


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.markdown(
    """
    <style>
    .react-datepicker__day--today {
        border-radius: 50% !important;
        border: 2px solid #ff4b4b !important;
        font-weight: bold !important;
        color: #ff4b4b !important;
    }
    .react-datepicker__day--today.react-datepicker__day--selected {
        color: #ffffff !important;
        background-color: #ff4b4b !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🐾 PawPal+")

st.markdown(
    """


"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

"""
    )

st.divider()

st.subheader("Owner and Pets")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat"])

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

if "editing_owner_for_names" not in st.session_state:
    st.session_state.editing_owner_for_names = None

if st.session_state.owners:
    st.write("**Saved owners:**")
    for idx, o in enumerate(st.session_state.owners):
        pet_names = ", ".join(p.name for p in o.pets)
        col_text, col_btn = st.columns([5, 1])
        with col_text:
            st.write(f"- {o.name} — pets: {pet_names}")
        with col_btn:
            if st.button("Edit", key=f"edit_owner_{idx}"):
                st.session_state.editing_owner_for_names = o
                show_edit_owner_dialog()
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
        pet_options = ["All Pets"] + [p.name for p in selected_owner.pets]
        selected_pet_name = st.selectbox("Pet", pet_options)
        selected_pet = (
            None if selected_pet_name == "All Pets"
            else next(p for p in selected_owner.pets if p.name == selected_pet_name)
        )

        with st.expander("✨ Smart Task Input", expanded=False):
            if selected_pet_name == "All Pets":
                st.caption(
                    "Describe tasks in plain English — one per line. "
                    "Include each pet's name in the task so it gets assigned correctly."
                )
            else:
                st.caption(
                    "Describe tasks in plain English — one per line. "
                    "Priority, duration, and time are filled in automatically using pet care rules."
                )
            all_pets_placeholder = (
                "Kimchi has a vet appointment at 5pm on 4/27\n"
                "Mochi should walk after breakfast for 15 min\n"
                "Kimchi needs meds at 3pm daily"
            )
            single_pet_placeholder = (
                "Give medication at 8am\nWalk after breakfast\nVet appointment next Tuesday"
            )
            smart_input = st.text_area(
                "Task descriptions",
                placeholder=all_pets_placeholder if selected_pet_name == "All Pets" else single_pet_placeholder,
                key="smart_task_input",
                height=110,
                label_visibility="collapsed",
            )
            if st.button("Add Tasks", key="parse_tasks_btn", type="primary"):
                if not smart_input.strip():
                    st.warning("Enter at least one task description.")
                else:
                    try:
                        from rag_helper import parse_tasks_with_rag, find_lines_missing_pet_name
                        if selected_pet_name == "All Pets":
                            all_pet_names = [p.name for p in selected_owner.pets]
                            input_lines = [l for l in smart_input.strip().splitlines() if l.strip()]
                            missing = find_lines_missing_pet_name(input_lines, all_pet_names)
                            if missing:
                                pet_list = ", ".join(all_pet_names)
                                st.error(
                                    f"Each task must mention a pet name ({pet_list}). "
                                    f"The following line{'s' if len(missing) > 1 else ''} "
                                    f"didn't match any pet:\n\n"
                                    + "\n".join(f"• {l}" for l in missing)
                                )
                                st.stop()
                            parsed_tasks, rag_warnings = parse_tasks_with_rag(smart_input.strip(), "All Pets", pet_names=all_pet_names, existing_tasks=[t for p in selected_owner.pets for t in p.tasks])
                        else:
                            parsed_tasks, rag_warnings = parse_tasks_with_rag(smart_input.strip(), selected_pet_name, existing_tasks=[t for p in selected_owner.pets for t in p.tasks])
                        for w in rag_warnings:
                            st.warning(w)

                        def _rag_task_window(t):
                            s = datetime.datetime.strptime(t.scheduled_time, "%H:%M")
                            return s, s + datetime.timedelta(minutes=t.duration_minutes)

                        def _rag_dates_overlap(t1, t2):
                            if not t1.start_date or not t2.start_date:
                                return True
                            s1 = datetime.date.fromisoformat(t1.start_date)
                            e1 = datetime.date.fromisoformat(t1.end_date) if t1.end_date else s1
                            s2 = datetime.date.fromisoformat(t2.start_date)
                            e2 = datetime.date.fromisoformat(t2.end_date) if t2.end_date else s2
                            return s1 <= e2 and s2 <= e1

                        def _rag_find_conflict(new_task, check_against):
                            n_start, n_end = _rag_task_window(new_task)
                            for existing in check_against:
                                if existing.is_complete:
                                    continue
                                if not _rag_dates_overlap(new_task, existing):
                                    continue
                                same_day = (
                                    existing.frequency == "daily"
                                    or new_task.frequency == "daily"
                                    or existing.scheduled_day == new_task.scheduled_day
                                )
                                if not same_day:
                                    continue
                                ex_start, ex_end = _rag_task_window(existing)
                                if n_start < ex_end and ex_start < n_end:
                                    return existing
                            return None

                        all_existing = [t for pet in selected_owner.pets for t in pet.tasks]
                        added, skipped, unmatched, batch = [], [], [], []

                        for new_task in parsed_tasks:
                            if selected_pet_name == "All Pets":
                                target_pet = next(
                                    (p for p in selected_owner.pets if p.name == new_task.pet_name),
                                    None,
                                )
                                if target_pet is None:
                                    unmatched.append(new_task)
                                    continue
                            else:
                                target_pet = selected_pet
                            conflict = _rag_find_conflict(new_task, all_existing + batch)
                            if conflict:
                                skipped.append((new_task, conflict))
                            else:
                                target_pet.add_task(new_task)
                                batch.append(new_task)
                                added.append(new_task)

                        if added:
                            if selected_pet_name == "All Pets":
                                names = ", ".join(sorted({t.pet_name for t in added}))
                                st.success(f"Added {len(added)} task(s) across: {names}.")
                            else:
                                st.success(f"Added {len(added)} task(s) to {selected_pet_name}'s schedule.")
                        for new_task in unmatched:
                            st.warning(
                                f"'{new_task.name}' was skipped — no pet name detected. "
                                f"Mention a pet name in the task description."
                            )
                        for new_task, conflict in skipped:
                            ex_s, ex_e = _rag_task_window(conflict)
                            st.warning(
                                f"'{new_task.name}' was skipped — conflicts with "
                                f"'{conflict.name}' ({ex_s.strftime('%H:%M')}–{ex_e.strftime('%H:%M')}). "
                                f"Edit the task to adjust its time."
                            )
                        if added:
                            st.rerun()
                    except Exception as e:
                        st.error(f"Could not parse tasks: {e}")

        if selected_pet is None:
            st.caption("Select a specific pet to add tasks manually.")
        else:
            st.markdown("##### Or add a task manually")
            col1, col2, col3 = st.columns(3)
            with col1:
                task_title = st.text_input("Task title", value="Morning walk")
            with col2:
                duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            with col3:
                priority = st.selectbox("Priority", ["low", "medium", "high", "non-negotiable"], index=2)

            single_day = st.checkbox("Single-day appointment")
            col4, col5, col6 = st.columns(3)
            with col4:
                frequency = st.selectbox("Frequency", ["daily", "weekly"], disabled=single_day)
            with col5:
                _add_time_opts = [
                    datetime.time(h, m).strftime("%I:%M %p").lstrip("0")
                    for h in range(24) for m in (0, 30)
                ]
                _add_time_24 = [
                    datetime.time(h, m).strftime("%H:%M")
                    for h in range(24) for m in (0, 30)
                ]
                _add_display_to_24 = dict(zip(_add_time_opts, _add_time_24))
                _add_time_display = st.selectbox("Time", _add_time_opts, index=16, key="add_task_time")
                scheduled_time_str = _add_display_to_24[_add_time_display]
            with col6:
                days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                scheduled_day = st.selectbox("Day (weekly only)", days_of_week, disabled=(single_day or frequency == "daily"))
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                task_start_date = st.date_input("Start date", value=datetime.date.today(), format="MM/DD/YYYY")
            with col_date2:
                if single_day:
                    task_end_date = task_start_date
                    st.date_input("End date", value=task_start_date, format="MM/DD/YYYY", disabled=True)
                else:
                    task_end_date = st.date_input("End date", value=datetime.date.today() + datetime.timedelta(days=7), format="MM/DD/YYYY")

            if st.button("Add task"):
                if not task_title.strip():
                    st.error("Task name cannot be empty.")
                elif task_end_date < task_start_date:
                    st.error("End date cannot be before start date.")
                else:
                    new_task = Task(
                        name=task_title.strip(),
                        duration_minutes=int(duration),
                        priority=priority,
                        category="general",
                        frequency=frequency,
                        scheduled_time=scheduled_time_str,
                        scheduled_day=scheduled_day,
                        start_date=task_start_date.isoformat(),
                        end_date=task_end_date.isoformat(),
                    )

                    def task_window(task):
                        start = datetime.datetime.strptime(task.scheduled_time, "%H:%M")
                        end = start + datetime.timedelta(minutes=task.duration_minutes)
                        return start, end

                    def date_ranges_overlap(t1, t2):
                        if not t1.start_date or not t2.start_date:
                            return True
                        s1 = datetime.date.fromisoformat(t1.start_date)
                        e1 = datetime.date.fromisoformat(t1.end_date) if t1.end_date else s1
                        s2 = datetime.date.fromisoformat(t2.start_date)
                        e2 = datetime.date.fromisoformat(t2.end_date) if t2.end_date else s2
                        return s1 <= e2 and s2 <= e1

                    all_existing = [t for pet in selected_owner.pets for t in pet.tasks]
                    conflict = None
                    new_start, new_end = task_window(new_task)
                    for existing in all_existing:
                        if existing.is_complete:
                            continue
                        if not date_ranges_overlap(new_task, existing):
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

        display_pet_tasks = (
            [(p, i, t) for p in selected_owner.pets for i, t in enumerate(p.tasks)]
            if selected_pet_name == "All Pets"
            else [(selected_pet, i, t) for i, t in enumerate(selected_pet.tasks)]
        )
        if display_pet_tasks:
            st.write("Current tasks:")
            for task_pet, i, task in display_pet_tasks:
                col_check, col_status, col_edit, col_delete = st.columns([3, 1, 1, 1])
                with col_check:
                    import datetime as _dt_fmt
                    try:
                        time_str = _dt_fmt.datetime.strptime(task.scheduled_time, "%H:%M").strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        time_str = task.scheduled_time
                    if task.start_date and task.end_date and task.start_date != task.end_date:
                        try:
                            s = _dt_fmt.date.fromisoformat(task.start_date).strftime("%-m/%-d/%Y")
                            e = _dt_fmt.date.fromisoformat(task.end_date).strftime("%-m/%-d/%Y")
                            date_str = f"{s} – {e}"
                        except Exception:
                            date_str = f"{task.start_date} – {task.end_date}"
                    elif task.start_date:
                        try:
                            date_str = _dt_fmt.date.fromisoformat(task.start_date).strftime("%-m/%-d/%Y")
                        except Exception:
                            date_str = task.start_date
                    else:
                        date_str = "No date"
                    pet_label = f" [{task.pet_name}]" if selected_pet_name == "All Pets" else ""
                    st.write(f"**{task.name}**{pet_label} — {task.priority} priority · {date_str} · {time_str} · {task.duration_minutes} min")
                with col_status:
                    if task.is_complete:
                        st.success("✅ Done")
                with col_edit:
                    if st.button("Edit", key=f"edit_{selected_owner_name}_{task_pet.name}_{i}"):
                        st.session_state.editing_task_index = i
                        st.session_state.editing_pet = task_pet
                        st.session_state.editing_owner = selected_owner
                        show_edit_task_dialog()
                with col_delete:
                    if st.button("Delete", key=f"delete_{selected_owner_name}_{task_pet.name}_{i}"):
                        if task.priority == "non-negotiable":
                            st.session_state.deleting_pet = task_pet
                            st.session_state.deleting_task = task
                            st.session_state.deleting_task_index = i
                            show_delete_confirmation()
                        else:
                            task_pet.remove_task(task)
                            if st.session_state.editing_task_index == i:
                                st.session_state.editing_task_index = None
                            st.rerun()

        else:
            st.info("No tasks yet. Add one above.")

        st.divider()

        # st.subheader("Build Schedule")
        # st.caption(f"Schedule for {selected_owner_name} — all pets")

        # if st.button("Generate schedule"):
        #     scheduler = Scheduler(selected_owner)
        #     plan = scheduler.generate_plan()
        #     st.session_state["last_plan_scheduler"] = scheduler
        #     st.session_state["last_plan"] = plan
        #     all_tasks = [task for pet in selected_owner.pets for task in pet.tasks]
        #     st.write(scheduler.explain_plan(all_tasks))

        # if "last_plan_scheduler" in st.session_state and st.session_state["last_plan"]:
        #     if st.button("Sort by Time"):
        #         sorted_tasks = st.session_state["last_plan_scheduler"].sort_by_time(st.session_state["last_plan"])
        #         st.markdown("**Tasks sorted by scheduled time:**")
        #         for task in sorted_tasks:
        #             st.write(f"`{task.scheduled_time}` — {task.name} [{task.pet_name}] ({task.priority}, {task.duration_minutes} min)")

        st.divider()
        st.subheader("Weekly Planner")
        st.caption("Press **Generate weekly schedule** after adding new tasks to update the calendar.")

        weekly_owner_name = st.selectbox("Owner", [o.name for o in st.session_state.owners], key="weekly_owner_filter")
        weekly_owner = next(o for o in st.session_state.owners if o.name == weekly_owner_name)

        pet_filter_options = ["All Pets"] + [p.name for p in weekly_owner.pets]
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
            scheduler = Scheduler(weekly_owner)
            st.session_state["last_weekly_scheduler"] = scheduler

        if "last_weekly_scheduler" in st.session_state:
            today = datetime.date.today()
            weekly = st.session_state["last_weekly_scheduler"].generate_weekly_schedule(pet_name=selected_pet_filter)

            priority_colors = {
                "non-negotiable": {"bg": "#ffaaaa", "border": "#cc3333"},
                "high":           {"bg": "#ffcc88", "border": "#cc6600"},
                "medium":         {"bg": "#fff099", "border": "#ccaa00"},
                "low":            {"bg": "#aaddaa", "border": "#337733"},
            }

            # Collect tasks for the selected pet filter, then expand each by its date range
            all_cal_tasks = [t for p in weekly_owner.pets for t in p.tasks if not t.is_complete]
            if selected_pet_filter != "All Pets":
                all_cal_tasks = [t for t in all_cal_tasks if t.pet_name == selected_pet_filter]

            events = []
            for t in all_cal_tasks:
                if not t.start_date:
                    continue
                t_start = datetime.date.fromisoformat(t.start_date)
                t_end = datetime.date.fromisoformat(t.end_date) if t.end_date else t_start
                end_time_obj = (
                    datetime.datetime.strptime(t.scheduled_time, "%H:%M")
                    + datetime.timedelta(minutes=t.duration_minutes)
                )
                end_str = end_time_obj.strftime('%H:%M')
                colors = priority_colors.get(t.priority, {"bg": "#cccccc", "border": "#888888"})

                current = t_start
                while current <= t_end:
                    if t.frequency == "weekly" and current.strftime("%A") != t.scheduled_day:
                        current += datetime.timedelta(days=1)
                        continue
                    done_key = f"done_{t.name}_{t.pet_name}_{current.isoformat()}_{t.scheduled_time}"
                    is_done = st.session_state.get(done_key, False)
                    events.append({
                        "id": done_key,
                        "title": f"✅ {t.name} [{t.pet_name}]" if is_done else f"{t.name} [{t.pet_name}]",
                        "start": f"{current.isoformat()}T{t.scheduled_time}:00",
                        "end":   f"{current.isoformat()}T{end_str}:00",
                        "backgroundColor": "#d0d0d0" if is_done else colors["bg"],
                        "borderColor":     "#999999" if is_done else colors["border"],
                        "textColor":       "#888888" if is_done else "#333333",
                        "extendedProps": {
                            "name":     t.name,
                            "petName":  t.pet_name,
                            "date":     current.isoformat(),
                            "start":    t.scheduled_time,
                            "end":      end_str,
                            "duration": t.duration_minutes,
                            "priority": t.priority,
                        },
                    })
                    current += datetime.timedelta(days=1)

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
                    "right":  "dayGridMonth,timeGridWeek,timeGridDay",
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
                    <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:8px; align-items:center;">
                        <span style="font-weight:600; font-size:0.85rem;">Priority:</span>
                        <span style="display:flex; align-items:center; gap:5px; font-size:0.82rem;">
                            <span style="width:14px; height:14px; border-radius:3px; background:#ffaaaa; border:2px solid #cc3333; display:inline-block;"></span> Non-negotiable
                        </span>
                        <span style="display:flex; align-items:center; gap:5px; font-size:0.82rem;">
                            <span style="width:14px; height:14px; border-radius:3px; background:#ffcc88; border:2px solid #cc6600; display:inline-block;"></span> High
                        </span>
                        <span style="display:flex; align-items:center; gap:5px; font-size:0.82rem;">
                            <span style="width:14px; height:14px; border-radius:3px; background:#fff099; border:2px solid #ccaa00; display:inline-block;"></span> Medium
                        </span>
                        <span style="display:flex; align-items:center; gap:5px; font-size:0.82rem;">
                            <span style="width:14px; height:14px; border-radius:3px; background:#aaddaa; border:2px solid #337733; display:inline-block;"></span> Low
                        </span>
                        <span style="display:flex; align-items:center; gap:5px; font-size:0.82rem;">
                            <span style="width:14px; height:14px; border-radius:3px; background:#d0d0d0; border:2px solid #999999; display:inline-block;"></span> Completed
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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

