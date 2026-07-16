"""Tests for algorithm evaluation: test cases + judge + report."""

import pytest

from tests.test_generator.cases import CORE_TEST_CASES
from timetable_generator.generator.evaluation import CaseResult, generate_eval_report
from timetable_generator.generator.judge import JudgeScore, judge
from timetable_generator.generator.retry import generate_with_retry
from timetable_generator.models.work_hour import WorkHourRecord


def test_judge_function_basic():
    """Judge function produces all expected fields."""
    records = [WorkHourRecord("p1", "u1", d, 8) for d in
               [__import__("datetime").date(2026, 3, 2),
                __import__("datetime").date(2026, 3, 4),
                __import__("datetime").date(2026, 3, 6)]]
    score = judge(
        records=records,
        validation=type("V", (), {"is_valid": True})(),
        target_ratio=0.5,
        actual_ratio=0.5,
        retry_count=1,
    )
    assert isinstance(score, JudgeScore)
    assert score.ratio_accuracy == 1.0
    assert score.hard_constraint_pass is True
    assert score.full_load_ratio == 1.0
    assert score.retry_count == 1
    assert score.overall_score > 0


def test_judge_hard_constraint_fail_zeros_score():
    score = judge(
        records=[],
        validation=type("V", (), {"is_valid": False})(),
        target_ratio=0.5,
        actual_ratio=0.0,
        retry_count=5,
    )
    assert score.overall_score == 0.0


def test_evaluation_report_generated(tmp_path):
    """Report is generated as Markdown with expected fields."""
    results = [
        CaseResult(
            case_id="tc_test",
            description="测试用例",
            score=JudgeScore(
                ratio_accuracy=0.98, hard_constraint_pass=True,
                full_load_ratio=1.0, jitter_naturalness=0.75,
                retry_count=2, overall_score=0.88,
            ),
            actual_hours=40, target_hours=40,
        ),
    ]
    report_path = generate_eval_report(results, tmp_path / "eval_report.md")
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "ratio_accuracy" not in content  # Report uses Chinese labels, not field names
    assert "硬约束通过率" in content
    assert "综合分" in content
    assert "是否可进入下一步" in content
    assert "tc_test" in content


@pytest.mark.parametrize("case", CORE_TEST_CASES, ids=[c.id for c in CORE_TEST_CASES])
def test_all_core_cases_pass_hard_constraints(case):
    """Each core test case should pass hard constraints when generated."""
    result = generate_with_retry(
        projects=case.projects,
        staff_states=case.staff,
        holidays=case.holidays,
        global_span=case.global_span,
        max_retries=10,
    )
    assert result.validation.is_valid, f"Case {case.id} failed: {result.validation.violations}"


@pytest.mark.parametrize("case", CORE_TEST_CASES, ids=[c.id for c in CORE_TEST_CASES])
def test_all_core_cases_ratio_within_tolerance(case):
    """Each core test case should achieve target ratio within 5% tolerance."""
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


def test_full_evaluation_report(tmp_path):
    """Run all core cases, generate full evaluation report."""
    results: list[CaseResult] = []
    for case in CORE_TEST_CASES:
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
            results.append(CaseResult(
                case_id=case.id,
                description=case.description,
                score=score,
                actual_hours=actual_h,
                target_hours=target_h,
            ))

    report_path = generate_eval_report(results, tmp_path / "eval_core.md",
                                       title="Generator Core 评估报告")
    content = report_path.read_text(encoding="utf-8")
    # All hard constraints should pass
    assert "全通过 ✅" in content
