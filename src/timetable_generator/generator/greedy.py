"""Two-phase greedy generator.

Phase 1: Project-person assignment — for each project, greedily assign persons
based on target ratio (overselling allowed: one person can join multiple projects).

Phase 2: Daily hour filling — for each (project, person) pair, fill hours day by day:
- Same day can split across projects (e.g., A 4h + B 4h), daily total = 8h.
- Adjacent day same-project hour diff ≤ 2h (no jumping).
- Each continuous spurt ≥ 3 days; gaps between spurts allowed.
- 1h granularity, full 8h/day when active.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date

from timetable_generator.generator.capacity import compute_capacity, compute_workdays
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord

FULL_DAY_HOURS = 8
MAX_DAY_JUMP = 2  # |hours(t+1) - hours(t)| <= 2
MIN_SPURT_DAYS = 3  # each continuous spurt >= 3 days (soft)


def generate_single(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,
) -> list[WorkHourRecord]:
    """Backward compat — delegates to generate()."""
    return generate(projects, staff_states, holidays, global_span, rng)


def generate(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,
) -> list[WorkHourRecord]:
    """Two-phase greedy generation."""
    if rng is None:
        rng = random.Random()

    workdays = compute_workdays(global_span, holidays)
    if not workdays or not projects:
        return []

    total_capacity = compute_capacity(staff_states, holidays, global_span)
    remaining: dict[str, int] = {}
    for project in projects:
        remaining[project.id] = int(total_capacity * project.target_ratio)

    person_day_hours: dict[tuple[str, date], int] = defaultdict(int)
    last_hours: dict[tuple[str, str], int] = {}
    records: list[WorkHourRecord] = []
    staff_by_id = {s.person_id: s for s in staff_states}

    # Sort projects by target_ratio ascending — small ratio first,
    # large ratio last (fills remaining daily capacity, ensuring 8h/day)
    sorted_projects = sorted(projects, key=lambda p: p.target_ratio)
    for project in sorted_projects:
        if remaining[project.id] <= 0:
            continue
        persons = list(project.associated_person_ids)
        rng.shuffle(persons)
        for person_id in persons:
            if remaining[project.id] <= 0:
                break
            state = staff_by_id.get(person_id)
            if state is None:
                continue
            person_wds = [
                wd
                for wd in workdays
                if state.is_active_on(wd) and project.start_date <= wd <= project.end_date
            ]
            if not person_wds:
                continue
            _fill_person_project(
                project.id,
                person_id,
                person_wds,
                remaining,
                person_day_hours,
                last_hours,
                records,
                rng,
            )
    return records


def _fill_person_project(
    project_id: str,
    person_id: str,
    workdays: list[date],
    remaining: dict[str, int],
    person_day_hours: dict[tuple[str, date], int],
    last_hours: dict[tuple[str, str], int],
    records: list[WorkHourRecord],
    rng: random.Random,
) -> None:
    """Fill hours for one (project, person) pair using spurts with jump constraint."""
    sorted_wds = sorted(workdays)
    proj_rem = remaining[project_id]
    key = (project_id, person_id)
    prev_h = last_hours.get(key, 0)

    i = 0
    while i < len(sorted_wds) and proj_rem > 0:
        # Find consecutive run of available days
        run: list[date] = []
        j = i
        while j < len(sorted_wds):
            avail = FULL_DAY_HOURS - person_day_hours[(person_id, sorted_wds[j])]
            if avail <= 0:
                break
            if j > i and (sorted_wds[j] - sorted_wds[j - 1]).days > 1:
                break
            run.append(sorted_wds[j])
            j += 1

        if not run:
            i = max(j, i + 1)
            continue

        # Count total available days (from i onward) for avg calculation
        avail_days = sum(
            1 for wd in sorted_wds[i:] if FULL_DAY_HOURS - person_day_hours[(person_id, wd)] > 0
        )
        # avg_h: target hours per day.
        # If enough quota for all available days at 8h → fill 8h (clamped to avail per day).
        # Otherwise spread across available days.
        if avail_days > 0 and proj_rem >= avail_days * FULL_DAY_HOURS:
            avg_h = FULL_DAY_HOURS  # Will be clamped to avail per day
        elif avail_days > 0:
            avg_h = max(1, min(8, proj_rem // avail_days))
        else:
            avg_h = 1
        # Fill each day in the run
        for k, wd in enumerate(run):
            if proj_rem <= 0:
                break
            avail = FULL_DAY_HOURS - person_day_hours[(person_id, wd)]
            if avail <= 0:
                continue

            if k == 0 and prev_h > 0:
                # Respect jump from previous spurt's last day
                h = max(prev_h - MAX_DAY_JUMP, min(prev_h + MAX_DAY_JUMP, avg_h))
            elif k > 0:
                # Jump constraint within spurt
                h = max(prev_h - MAX_DAY_JUMP, min(prev_h + MAX_DAY_JUMP, avg_h))
            else:
                h = avg_h

            h = max(1, min(8, h, avail, proj_rem))

            records.append(
                WorkHourRecord(
                    project_id=project_id,
                    person_id=person_id,
                    date=wd,
                    hours=h,
                )
            )
            person_day_hours[(person_id, wd)] += h
            proj_rem -= h
            prev_h = h

        # Distribute leftover quota (from integer division) across the run
        if proj_rem > 0:
            for wd in reversed(run):
                if proj_rem <= 0:
                    break
                avail = FULL_DAY_HOURS - person_day_hours[(person_id, wd)]
                if avail <= 0:
                    continue
                add = min(1, avail, proj_rem)
                # Replace the record with updated hours
                for idx, r in enumerate(records):
                    if r.project_id == project_id and r.person_id == person_id and r.date == wd:
                        records[idx] = WorkHourRecord(
                            project_id=project_id,
                            person_id=person_id,
                            date=wd,
                            hours=r.hours + add,
                        )
                        break
                person_day_hours[(person_id, wd)] += add
                proj_rem -= add

        remaining[project_id] = proj_rem
        last_hours[key] = prev_h
        i = j
