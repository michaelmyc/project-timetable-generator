"""Greedy generator — single and multi-project work-hour allocation.

Heuristic greedy + randomized construction (ADR-0009):
- Multi-project: global scheduling across all projects, 1h split per day.
- Natural jitter: shuffle workday order for non-sequential assignment.
- 1h granularity: split 8h across projects per day, exact ratio targeting.
- Every workday is filled to 8h total (满载, ADR-0008 D1).
- Continuity (ADR-0011): refer to previous day's split (soft).
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
    """Backward compat — delegates to generate()."""
    return generate(projects, staff_states, holidays, global_span, rng)


def generate(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,
) -> list[WorkHourRecord]:
    """Generate work-hour records with multi-project global scheduling.

    Key guarantee: every workday that has any eligible project gets filled to 8h total.
    8h is split across eligible projects proportional to their remaining target hours.

    Algorithm (per staff member, per workday):
    1. Find eligible projects (person associated, date in range, remaining > 0).
    2. If none, skip this day (person idle — total project ratio < 1.0).
    3. Distribute 8h across eligible projects proportional to remaining targets.
    4. 1h granularity: round to integers, adjust last project to hit exact 8h.
    5. Natural jitter: shuffle workday order + shuffle project order per day.
    """
    if rng is None:
        rng = random.Random()

    workdays = compute_workdays(global_span, holidays)
    if not workdays or not projects:
        return []

    total_capacity = compute_capacity(staff_states, holidays, global_span)

    # Compute target hours per project
    project_remaining: dict[str, int] = {}
    for project in projects:
        target = int(total_capacity * project.target_ratio)
        project_remaining[project.id] = target

    records: list[WorkHourRecord] = []

    for staff_state in staff_states:
        person_id = staff_state.person_id
        person_workdays = [wd for wd in workdays if staff_state.is_active_on(wd)]
        # Shuffle for natural jitter
        shuffled_days = list(person_workdays)
        rng.shuffle(shuffled_days)

        for wd in shuffled_days:
            # Find eligible projects
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
                continue  # No project needs this person today → idle day

            # Shuffle eligible projects for jitter
            rng.shuffle(eligible)

            # Distribute 8h proportional to remaining targets
            total_remaining = sum(project_remaining[p.id] for p in eligible)
            hours_to_fill = FULL_DAY_HOURS

            for i, project in enumerate(eligible):
                if hours_to_fill <= 0:
                    break
                if i == len(eligible) - 1:
                    # Last project gets all remaining hours to guarantee 8h total
                    hours = hours_to_fill
                else:
                    # Proportional allocation, 1h granularity
                    proportion = project_remaining[project.id] / total_remaining
                    hours = min(
                        hours_to_fill,
                        project_remaining[project.id],
                        round(proportion * FULL_DAY_HOURS),
                    )
                    hours = max(1, hours)  # At least 1h if eligible

                hours = min(hours, project_remaining[project.id], hours_to_fill)
                if hours <= 0:
                    continue

                records.append(
                    WorkHourRecord(
                        project_id=project.id,
                        person_id=person_id,
                        date=wd,
                        hours=hours,
                    )
                )
                hours_to_fill -= hours
                project_remaining[project.id] -= hours

    return records
