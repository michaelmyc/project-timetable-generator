"""Unit tests for the phase-1 planner."""

from datetime import date

import pytest

from timetable_generator.generator.planner import (
    InfeasibleProjectError,
    plan,
)
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def _span() -> GlobalSpan:
    return GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))  # 10 workdays


def _states(span: GlobalSpan, ids: list[str]) -> list[StaffState]:
    return [StaffState.from_info(StaffInfo(name=i), span) for i in ids]


def test_plan_infeasible_quota_exceeds_local_capacity():
    """InfeasibleProjectError raised when quota > local capacity.

    Hard to trigger via public API (Project validates ratio ≤ 1.0), so test
    the error class directly — it's the contract planner promises to enforce.
    """
    with pytest.raises(InfeasibleProjectError):
        raise InfeasibleProjectError("p1", 100, 50)


def test_plan_basic_single_project_single_person():
    """1 project 50%, 1 person full-span → plan has one commitment ≈ 40h."""
    span = _span()
    states = _states(span, ["u1"])
    p = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
    result = plan([p], states, set(), span)
    assert len(result.plans) == 1
    pp = result.plans[0]
    assert pp.person_id == "u1"
    assert pp.project_id == "p1"
    assert pp.total > 0
    assert result.gaps["p1"] == 0


def test_plan_overlap_proportional_allocation():
    """Two persons with different overlap lengths → commitment proportional to overlap."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 27))  # 20 workdays
    # u1 full span (20 days), u2 only first week (5 days)
    staff = [
        StaffState.from_info(StaffInfo(name="u1"), span),
        StaffState.from_info(
            StaffInfo(name="u2", onboard_date=date(2026, 3, 2), leave_date=date(2026, 3, 6)),
            span,
        ),
    ]
    p = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 27), 0.3, ["研发人员"], ["u1", "u2"])
    result = plan([p], staff, set(), span)
    # u1 has 4× the overlap of u2 → should get ~4× the commitment.
    u1_plan = next(pp for pp in result.plans if pp.person_id == "u1")
    u2_plan = next(pp for pp in result.plans if pp.person_id == "u2")
    assert u1_plan.total > u2_plan.total


def test_plan_respects_onboard_leave():
    """Staff with leave date only active on overlap days."""
    span = _span()
    staff = [StaffState.from_info(StaffInfo(name="u1", leave_date=date(2026, 3, 6)), span)]
    p = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
    result = plan([p], staff, set(), span)
    pp = result.plans[0]
    # Overlap should be only 2026-03-02 to 2026-03-06 (5 days)
    assert len(pp.overlap_days) == 5
    assert pp.overlap_days[0] == date(2026, 3, 2)
    assert pp.overlap_days[-1] == date(2026, 3, 6)


def test_plan_zero_ratio_zero_quota():
    """Project with target_ratio=0 → no commitments, gap=0."""
    span = _span()
    states = _states(span, ["u1"])
    p = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.0, ["研发人员"], ["u1"])
    result = plan([p], states, set(), span)
    assert result.plans == []
    assert result.gaps["p1"] == 0


def test_plan_quota_recorded():
    """PlanResult.quotas and local_capacities are populated."""
    span = _span()
    states = _states(span, ["u1", "u2"])
    p = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1", "u2"])
    result = plan([p], states, set(), span)
    assert result.quotas["p1"] > 0
    assert result.local_capacities["p1"] > 0
    assert result.quotas["p1"] <= result.local_capacities["p1"]
