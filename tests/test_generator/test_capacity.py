"""Tests for capacity calculation."""

from datetime import date

from timetable_generator.generator.capacity import compute_capacity, compute_workdays
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_compute_workdays_no_holidays():
    """2 weeks, no holidays → 10 workdays (Mon-Fri)."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))  # Mon–Fri next week
    holidays: set[date] = set()
    workdays = compute_workdays(span, holidays)
    assert len(workdays) == 10  # 2 weeks × 5 days


def test_compute_workdays_with_holiday():
    """1 week with 1 holiday → 4 workdays."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    holidays = {date(2026, 3, 3)}  # Tuesday holiday
    workdays = compute_workdays(span, holidays)
    assert len(workdays) == 4


def test_compute_workdays_excludes_weekends():
    span = GlobalSpan(date(2026, 3, 7), date(2026, 3, 8))  # Sat, Sun
    holidays: set[date] = set()
    workdays = compute_workdays(span, holidays)
    assert len(workdays) == 0


def test_capacity_single_person():
    """1 person, 2 weeks, no holidays → 10 workdays × 8h = 80h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    staff = [StaffState.from_changes("u1", [], span)]
    holidays: set[date] = set()
    capacity = compute_capacity(staff, holidays, span)
    assert capacity == 80  # 10 workdays × 8h


def test_capacity_two_persons():
    """2 persons, 1 week, no holidays → 2 × 5 × 8 = 80h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [
        StaffState.from_changes("u1", [], span),
        StaffState.from_changes("u2", [], span),
    ]
    holidays: set[date] = set()
    capacity = compute_capacity(staff, holidays, span)
    assert capacity == 80  # 2 persons × 5 workdays × 8h


def test_capacity_excludes_inactive_staff():
    """Person who left before span → 0 contribution."""
    from timetable_generator.models.staff_change import StaffChangeRecord

    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    changes = [
        StaffChangeRecord("u1", date(2026, 1, 1), "onboard", "研发人员", None),
        StaffChangeRecord("u1", date(2026, 2, 1), "leave"),  # left before span
    ]
    staff = [StaffState.from_changes("u1", changes, span)]
    holidays: set[date] = set()
    capacity = compute_capacity(staff, holidays, span)
    assert capacity == 0  # u1 not active during span
