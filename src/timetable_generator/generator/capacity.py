"""Capacity calculation and ratio conversion for work-hour generation."""

from __future__ import annotations

from datetime import date

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
