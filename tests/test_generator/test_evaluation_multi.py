"""Multi-project evaluation tests."""

from collections import defaultdict

import pytest

from tests.test_generator.cases_multi import MULTI_TEST_CASES
from timetable_generator.generator.evaluation import CaseResult, generate_eval_report
from timetable_generator.generator.judge import judge
from timetable_generator.generator.retry import generate_with_retry


@pytest.mark.parametrize("case", MULTI_TEST_CASES, ids=[c.id for c in MULTI_TEST_CASES])
def test_multi_cases_pass_hard_constraints(case):
    """Each multi test case passes hard constraints."""
    result = generate_with_retry(
        projects=case.projects,
        staff_states=case.staff,
        holidays=case.holidays,
        global_span=case.global_span,
        max_retries=10,
    )
    assert result.validation.is_valid, f"Case {case.id} failed: {result.validation.violations}"


@pytest.mark.parametrize("case", MULTI_TEST_CASES, ids=[c.id for c in MULTI_TEST_CASES])
def test_multi_cases_cross_day_eq_8h(case):
    """When total ratio = 1.0, each person's daily total = 8h.
    When total ratio < 1.0, daily total should be <= 8h (not necessarily 8h)."""
    result = generate_with_retry(
        projects=case.projects,
        staff_states=case.staff,
        holidays=case.holidays,
        global_span=case.global_span,
        max_retries=10,
    )
    total_ratio = sum(p.target_ratio for p in case.projects)
    by_day: dict[tuple, int] = defaultdict(int)
    for r in result.records:
        by_day[(r.person_id, r.date)] += r.hours
    for key, total in by_day.items():
        assert total <= 8, f"Case {case.id} {key}: {total}h > 8h"
        if total_ratio >= 1.0:
            assert total == 8, f"Case {case.id} {key}: {total}h != 8h (total ratio=1.0)"


@pytest.mark.parametrize("case", MULTI_TEST_CASES, ids=[c.id for c in MULTI_TEST_CASES])
def test_multi_cases_ratio_within_tolerance(case):
    """Each project achieves target hours within 1h tolerance."""
    result = generate_with_retry(
        projects=case.projects,
        staff_states=case.staff,
        holidays=case.holidays,
        global_span=case.global_span,
        max_retries=10,
    )
    for pid, expected in case.expected_target_hours.items():
        actual = sum(r.hours for r in result.records if r.project_id == pid)
        assert abs(actual - expected) <= 1, (
            f"Case {case.id} project {pid}: expected {expected}h, got {actual}h"
        )


def test_multi_evaluation_report(tmp_path):
    """Generate full multi-project evaluation report."""
    results: list[CaseResult] = []
    for case in MULTI_TEST_CASES:
        result = generate_with_retry(
            projects=case.projects,
            staff_states=case.staff,
            holidays=case.holidays,
            global_span=case.global_span,
            max_retries=10,
        )
        for pid, target_h in case.expected_target_hours.items():
            actual_h = sum(r.hours for r in result.records if r.project_id == pid)
            project = next(p for p in case.projects if p.id == pid)
            actual_ratio = result.validation.ratio_achievement.get(pid, 0.0)
            score = judge(
                records=[r for r in result.records if r.project_id == pid],
                validation=result.validation,
                target_ratio=project.target_ratio,
                actual_ratio=actual_ratio,
                retry_count=result.attempts,
            )
            results.append(
                CaseResult(
                    case_id=case.id,
                    description=case.description,
                    score=score,
                    actual_hours=actual_h,
                    target_hours=target_h,
                )
            )

    report_path = generate_eval_report(
        results,
        tmp_path / "eval_multi.md",
        title="Generator Multi 评估报告",
    )
    content = report_path.read_text(encoding="utf-8")
    assert "全通过 ✅" in content
