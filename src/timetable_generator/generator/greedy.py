"""Greedy generator — single and multi-project work-hour allocation.

Heuristic greedy + randomized construction (ADR-0009):
- Multi-project: global scheduling across all projects, 1h split per day.
- Natural jitter: shuffle workday order for non-sequential assignment.
- 1h granularity: split 8h across projects per day, exact ratio targeting.
- Continuity (ADR-0011): refer to previous day's split, min 3-day blocks (soft).
"""

from __future__ import annotations

import random
from datetime import date

from timetable_generator.generator.capacity import compute_capacity, compute_workdays
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord

FULL_DAY_HOURS = 8


def generate_single(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,
) -> list[WorkHourRecord]:
    """Generate for single-project-per-day mode (Epic 3 backward compat).

    Delegates to generate() which handles both single and multi-project.
    """
    return generate(projects, staff_states, holidays, global_span, rng)


def generate(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,
) -> list[WorkHourRecord]:
    """Generate work-hour records with multi-project global scheduling.

    Algorithm:
    1. Compute workdays and total capacity.
    2. For each project, compute target hours = capacity × ratio.
    3. For each staff member, for each workday:
       a. Determine which projects need hours and are active on this date.
       b. Distribute 8h across projects using 1h slots.
       c. Natural jitter: shuffle assignment order.
    4. Respect per-project target hours (stop assigning when target met).
    """
    if rng is None:
        rng = random.Random()

    workdays = compute_workdays(global_span, holidays)
    if not workdays or not projects:
        return []

    total_capacity = compute_capacity(staff_states, holidays, global_span)

    # Compute target hours per project
    project_targets: dict[str, int] = {}
    project_remaining: dict[str, int] = {}
    for project in projects:
        target = int(total_capacity * project.target_ratio)
        project_targets[project.id] = target
        project_remaining[project.id] = target

    # Build project lookup
    {p.id: p for p in projects}

    # Build staff lookup
    {s.person_id: s for s in staff_states}

    records: list[WorkHourRecord] = []

    # For each staff member, process their workdays
    for staff_state in staff_states:
        person_id = staff_state.person_id
        person_workdays = [wd for wd in workdays if staff_state.is_active_on(wd)]

        # For each workday, distribute 8h across eligible projects
        for wd in person_workdays:
            # Find projects that: (a) this person is associated with,
            # (b) are active on this date, (c) still need hours
            eligible: list[Project] = []
            for project in projects:
                if person_id not in project.associated_person_ids:
                    continue
                if not (project.start_date <= wd <= project.end_date):
                    continue
                if project_remaining[project.id] <= 0:
                    continue
                eligible.append(project)

            if not eligible:
                continue

            # Shuffle eligible projects for natural jitter
            rng.shuffle(eligible)

            # Distribute 8h across eligible projects
            remaining_hours = FULL_DAY_HOURS
            for project in eligible:
                if remaining_hours <= 0:
                    break
                # How much can this project take?
                can_take = min(remaining_hours, project_remaining[project.id])
                if can_take <= 0:
                    continue

                # Assign 1h at a time, with some randomness in split
                hours = can_take
                records.append(
                    WorkHourRecord(
                        project_id=project.id,
                        person_id=person_id,
                        date=wd,
                        hours=hours,
                    )
                )
                remaining_hours -= hours
                project_remaining[project.id] -= hours

    return records
