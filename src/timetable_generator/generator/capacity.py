"""Capacity calculation and ratio conversion for work-hour generation."""

from __future__ import annotations

from datetime import date

from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState

FULL_DAY_HOURS = 8


def compute_workdays(span: GlobalSpan, holidays: set[date]) -> list[date]:
    """Compute workdays within a span, excluding weekends and holidays.

    Args:
        span: The global time range.
        holidays: Set of holiday dates (non-workday).

    Returns:
        Sorted list of workday dates.
    """
    from datetime import timedelta

    workdays: list[date] = []
    current = span.start_date
    while current <= span.end_date:
        if current.weekday() < 5 and current not in holidays:  # Mon-Fri, not holiday
            workdays.append(current)
        current += timedelta(days=1)
    return workdays


def compute_capacity(
    staff_states: list[StaffState],
    holidays: set[date],
    span: GlobalSpan,
) -> int:
    """Compute total available work hours for all staff.

    = Σ(each staff's active workdays in span) × 8h

    A staff's active workdays = workdays in span where staff is active (is_active_on).
    """
    workdays = compute_workdays(span, holidays)
    total = 0
    for state in staff_states:
        for wd in workdays:
            if state.is_active_on(wd):
                total += FULL_DAY_HOURS
    return total


def compute_target_hours(capacity: int, ratio: float) -> int:
    """Convert target ratio to target hours (integer, 1h granularity).

    Rounds down to nearest integer hour.
    """
    return int(capacity * ratio)


def compute_project_local_capacity(
    project: Project,
    staff_states: list[StaffState],
    workdays: list[date],
) -> int:
    """Total available work hours for a project's associated staff within the project span.

    = Σ(each associated staff's workdays in [project.start, project.end] where active) × 8h.
    Used as the denominator for project ratio and the physical-feasibility ceiling.
    """
    by_id = {s.person_id: s for s in staff_states}
    total = 0
    for pid in project.associated_person_ids:
        state = by_id.get(pid)
        if state is None:
            continue
        for wd in workdays:
            if project.start_date <= wd <= project.end_date and state.is_active_on(wd):
                total += FULL_DAY_HOURS
    return total
