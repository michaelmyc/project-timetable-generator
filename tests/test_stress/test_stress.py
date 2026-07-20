"""Stress tests with quality gates.

CI runs the lightweight subset (baseline + tight_overlap, ci_cases each).
Full matrix runs manually: ``uv run pytest tests/test_stress/ -m stress --full``

Gates are set to the current algorithm's achievable quality (post two-phase
refactor). Target gates for M5 algorithm upgrade are noted inline; raising
these thresholds is the M5 "algorithm upgrade evaluation" acceptance criterion.
"""

from __future__ import annotations

import sys

import pytest

from tests.test_stress.framework import run_stress
from tests.test_stress.scenarios import SCENARIOS

# Current achievable gates (post two-phase refactor, before fill optimization).
# M5 target: success_rate_min=0.95, ratio_error_p90_max=0.05.
GATES = {
    "success_rate_min": 0.35,
    "ratio_error_p90_max": 0.45,
    "elapsed_p95_medium": 10.0,
    "elapsed_p95_large": 60.0,
}
LARGE_SCENARIOS = {"large"}


def _case_count(config, full: bool) -> int:
    return config.full_cases if full else config.ci_cases


@pytest.mark.stress
def test_baseline(write_report) -> None:
    """Baseline scenario — resource-abundant, validates basic stability."""
    from tests.test_stress.conftest import get_scenario

    cfg = get_scenario("baseline")
    report = run_stress(cfg, _case_count(cfg, "--full" in sys.argv))
    write_report(report, "baseline.json")
    _assert_gates(report, is_large=False)


@pytest.mark.stress
def test_tight_overlap(write_report) -> None:
    """Tight overlap — scarce overlap between project span and staff active window."""
    from tests.test_stress.conftest import get_scenario

    cfg = get_scenario("tight_overlap")
    report = run_stress(cfg, _case_count(cfg, "--full" in sys.argv))
    write_report(report, "tight_overlap.json")
    _assert_gates(report, is_large=False)


def _assert_gates(report, is_large: bool) -> None:
    """Assert quality gates. Print summary on failure for diagnosis."""
    cfg = report.config
    ok = True
    lines = [f"[{cfg.name}] {cfg.description}", *report.summary_lines()]

    if report.success_rate < GATES["success_rate_min"]:
        ok = False
        lines.append(
            f"  FAIL success_rate {report.success_rate:.1%} < {GATES['success_rate_min']:.0%}"
        )
    if report.ratio_error_p90 > GATES["ratio_error_p90_max"]:
        ok = False
        lines.append(
            f"  FAIL ratio_error_p90 {report.ratio_error_p90:.3f} > {GATES['ratio_error_p90_max']:.3f}"
        )
    elapsed_max = GATES["elapsed_p95_large"] if is_large else GATES["elapsed_p95_medium"]
    if report.elapsed_p95 > elapsed_max:
        ok = False
        lines.append(f"  FAIL elapsed_p95 {report.elapsed_p95:.2f}s > {elapsed_max}s")

    print("\n" + "\n".join(lines))
    assert ok, "\n".join(lines)


# Full matrix runner — not collected by default, invoked manually.
def _run_full_matrix(write_report) -> None:
    for cfg in SCENARIOS:
        report = run_stress(cfg, cfg.full_cases)
        write_report(report, f"{cfg.name}.json")
        _assert_gates(report, is_large=cfg.name in LARGE_SCENARIOS)
