"""Tests for multi-project generator — cross-project =8h, 1h split."""

from datetime import date

from timetable_generator.generator.greedy import generate
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_two_projects_same_person_cross_day_eq_8h():
    """1 person, 2 projects each 50% → each day total = 8h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))  # 2 weeks
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
    records = generate([p1, p2], staff, holidays=set(), global_span=span)
    # Group by (person, date) → sum should be 8h
    from collections import defaultdict

    by_day = defaultdict(int)
    for r in records:
        by_day[(r.person_id, r.date)] += r.hours
    for (pid, d), total in by_day.items():
        assert total >= 7, f"{pid} on {d}: {total}h (expect ~8h, allow 1h rounding)"


def test_two_projects_ratio_achievement():
    """2 projects each 50% → each gets ~40h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
    records = generate([p1, p2], staff, holidays=set(), global_span=span)
    p1_hours = sum(r.hours for r in records if r.project_id == "p1")
    p2_hours = sum(r.hours for r in records if r.project_id == "p2")
    # capacity = 80h, each target = 40h
    assert abs(p1_hours - 40) <= 2
    assert abs(p2_hours - 40) <= 2


def test_1h_split_precision_small_scale():
    """1 person, 5 workdays, 2 projects → 1h granularity for exact ratio."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))  # 5 workdays
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 6), 0.3, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 3, 6), 0.5, ["研发人员"], ["u1"])
    records = generate([p1, p2], staff, holidays=set(), global_span=span)
    # capacity = 40h, p1 target = 12h, p2 target = 20h
    p1_hours = sum(r.hours for r in records if r.project_id == "p1")
    p2_hours = sum(r.hours for r in records if r.project_id == "p2")
    assert abs(p1_hours - 12) <= 2
    assert abs(p2_hours - 20) <= 2
    # All hours are integers (1h granularity)
    assert all(isinstance(r.hours, int) for r in records)


def test_single_project_still_works():
    """Backward compat: single project via generate() still works."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 1.0, ["研发人员"], ["u1"])
    records = generate([p1], staff, holidays=set(), global_span=span)
    assert sum(r.hours for r in records) == 80  # 10 workdays × 8h
    assert all(r.hours == 8 for r in records)


def test_three_projects_split():
    """3 projects, 1 person → each gets correct ratio."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 27))  # 4 weeks = 20 workdays
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 27), 0.5, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 3, 27), 0.3, ["研发人员"], ["u1"])
    p3 = Project("p3", "C", date(2026, 3, 2), date(2026, 3, 27), 0.2, ["研发人员"], ["u1"])
    records = generate([p1, p2, p3], staff, holidays=set(), global_span=span)
    # capacity = 160h, targets: p1=80, p2=48, p3=32
    p1_h = sum(r.hours for r in records if r.project_id == "p1")
    p2_h = sum(r.hours for r in records if r.project_id == "p2")
    p3_h = sum(r.hours for r in records if r.project_id == "p3")
    assert abs(p1_h - 80) <= 2
    assert abs(p2_h - 48) <= 2
    assert abs(p3_h - 32) <= 2
    # Cross-day total = 8h
    from collections import defaultdict

    by_day = defaultdict(int)
    for r in records:
        by_day[(r.person_id, r.date)] += r.hours
    for total in by_day.values():
        assert total >= 7
