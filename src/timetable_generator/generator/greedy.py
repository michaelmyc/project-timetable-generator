"""Greedy generator core — single person/project work-hour allocation.

Heuristic greedy + randomized construction (ADR-0009):
- For each project, compute target hours from ratio.
- For single person + single project: assign full 8h to workdays until target met.
- Natural jitter: randomly select which workdays to assign (not sequential).
- 1h granularity: last day may get partial hours to hit exact target.
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
    """Generate work-hour records for single-person-single-project (or simple multi).

    MVP: supports one or more projects but each person works on at most one project per day.
    Full multi-project splitting is in Epic 4.

    Algorithm:
    1. Compute workdays (excluding holidays + weekends).
    2. For each project, compute target hours = capacity × ratio.
    3. For each staff member, distribute their available workdays across projects.
    4. Natural jitter: shuffle workday order for non-sequential assignment.
    5. 1h granularity: fill 8h per day until target reached; last day may be partial.
    """
    if rng is None:
        rng = random.Random()

    workdays = compute_workdays(global_span, holidays)
    if not workdays:
        return []

    records: list[WorkHourRecord] = []

    for project in projects:
        # Compute this project's target hours
        # Capacity = total staff available hours (all staff)
        total_capacity = compute_capacity(staff_states, holidays, global_span)
        target_hours = int(total_capacity * project.target_ratio)
        if target_hours <= 0:
            continue

        remaining = target_hours
        # Shuffle workdays for natural jitter
        shuffled = list(workdays)
        rng.shuffle(shuffled)

        for person_id in project.associated_person_ids:
            if remaining <= 0:
                break
            # Find this person's state
            person_state = next((s for s in staff_states if s.person_id == person_id), None)
            if person_state is None:
                continue

            # Get this person's active workdays
            person_workdays = [wd for wd in shuffled if person_state.is_active_on(wd)]
            # Project date range filter
            person_workdays = [
                wd for wd in person_workdays if project.start_date <= wd <= project.end_date
            ]

            for wd in person_workdays:
                if remaining <= 0:
                    break
                hours = min(FULL_DAY_HOURS, remaining)
                records.append(
                    WorkHourRecord(
                        project_id=project.id,
                        person_id=person_id,
                        date=wd,
                        hours=hours,
                    )
                )
                remaining -= hours

    return records
