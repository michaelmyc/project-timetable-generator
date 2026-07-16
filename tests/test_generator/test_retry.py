"""Tests for N-retry orchestration."""

from datetime import date

import pytest

from timetable_generator.generator.retry import GenerationError, generate_with_retry
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord


def test_retry_until_valid():
    """First 2 attempts produce invalid records, 3rd is valid."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 6),
        target_ratio=1.0, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )
    valid_records = [WorkHourRecord("p1", "u1", d, 8) for d in
                     [date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4),
                      date(2026, 3, 5), date(2026, 3, 6)]]
    call_count = 0

    def mock_greedy(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return []  # Empty = invalid (no job type coverage)
        return list(valid_records)

    result = generate_with_retry(
        projects=[project], staff_states=staff, holidays=set(),
        global_span=span, greedy_fn=mock_greedy, max_retries=10,
    )
    assert result.validation.is_valid
    assert call_count == 3


def test_retry_exhausted_raises():
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 6),
        target_ratio=1.0, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )

    def always_invalid(**kwargs):
        return []  # Always empty → never valid

    with pytest.raises(GenerationError) as exc_info:
        generate_with_retry(
            projects=[project], staff_states=staff, holidays=set(),
            global_span=span, greedy_fn=always_invalid, max_retries=3,
        )
    assert "3" in str(exc_info.value) or "retries" in str(exc_info.value).lower()


def test_first_attempt_success():
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 6),
        target_ratio=1.0, required_job_types=["研发人员"], associated_person_ids=["u1"],
    )
    valid_records = [WorkHourRecord("p1", "u1", d, 8) for d in
                     [date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4),
                      date(2026, 3, 5), date(2026, 3, 6)]]

    def good_greedy(**kwargs):
        return list(valid_records)

    result = generate_with_retry(
        projects=[project], staff_states=staff, holidays=set(),
        global_span=span, greedy_fn=good_greedy, max_retries=10,
    )
    assert result.validation.is_valid
