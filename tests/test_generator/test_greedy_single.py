"""Tests for greedy generator — single person single project."""

from datetime import date

from timetable_generator.generator.greedy import generate_single
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_single_person_single_project_full_ratio():
    """1 person, 2 weeks, ratio=1.0 → all workdays assigned 8h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))  # 2 weeks
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 13),
        target_ratio=1.0, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )
    holidays: set[date] = set()
    records = generate_single(
        projects=[project], staff_states=staff, holidays=holidays, global_span=span,
    )
    assert len(records) > 0
    assert all(r.hours == 8 for r in records)  # 满载
    assert sum(r.hours for r in records) == 10 * 8  # 10 workdays × 8h


def test_single_person_half_ratio():
    """1 person, 2 weeks, ratio=0.5 → ~40h assigned (5 workdays worth)."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 13),
        target_ratio=0.5, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )
    holidays: set[date] = set()
    records = generate_single(
        projects=[project], staff_states=staff, holidays=holidays, global_span=span,
    )
    # capacity = 10 workdays × 8h = 80h, target = 80 × 0.5 = 40h
    assert sum(r.hours for r in records) == 40
    assert all(r.hours <= 8 for r in records)


def test_single_person_small_scale_precision():
    """1 person, 5 workdays, ratio=0.3 → 12h (1h granularity)."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))  # 1 week, 5 workdays
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 6),
        target_ratio=0.3, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )
    holidays: set[date] = set()
    records = generate_single(
        projects=[project], staff_states=staff, holidays=holidays, global_span=span,
    )
    # capacity = 5 × 8 = 40h, target = 40 × 0.3 = 12h
    assert sum(r.hours for r in records) == 12


def test_single_person_holiday_excluded():
    """1 person, 1 week with 1 holiday, ratio=1.0 → 4 workdays × 8h = 32h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 6),
        target_ratio=1.0, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )
    holidays = {date(2026, 3, 3)}  # Tuesday holiday
    records = generate_single(
        projects=[project], staff_states=staff, holidays=holidays, global_span=span,
    )
    assert sum(r.hours for r in records) == 32  # 4 workdays × 8h
    assert all(r.date != date(2026, 3, 3) for r in records)  # no record on holiday
