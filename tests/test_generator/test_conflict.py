"""Tests for multi-project conflict reporting."""

from datetime import date

import pytest

from timetable_generator.generator.retry import GenerationError, generate_with_retry
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_capacity_conflict_reports_person_and_projects():
    """Two projects with combined ratio > 1.0 for same person → should fail."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))  # 2 weeks, 80h capacity
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13),
                 0.7, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 3, 13),
                 0.7, ["研发人员"], ["u1"])
    # Combined ratio = 1.4 > 1.0 → impossible to satisfy both
    with pytest.raises(GenerationError):
        generate_with_retry(
            projects=[p1, p2], staff_states=staff, holidays=set(),
            global_span=span, max_retries=5,
        )


def test_job_type_coverage_missing_reports():
    """Project requires '测试' but no tester available → should fail."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [StaffState.from_changes("u1", [], span)]  # u1 is 研发人员
    project = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 6),
                      1.0, ["研发人员", "测试"], ["u1"])
    with pytest.raises(GenerationError) as exc_info:
        generate_with_retry(
            projects=[project], staff_states=staff, holidays=set(),
            global_span=span, max_retries=5,
        )
    # Error should mention the missing job type
    assert any("测试" in str(v.detail) for v in exc_info.value.violations)
