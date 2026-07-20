"""Stress test conftest — fixtures and report output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_stress.framework import StressReport
from tests.test_stress.scenarios import SCENARIOS

REPORTS_DIR = Path(__file__).parent / "reports"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "stress: randomized quality evaluation")


@pytest.fixture
def reports_dir() -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    return REPORTS_DIR


@pytest.fixture
def write_report(reports_dir: Path) -> object:
    def _write(report: StressReport, filename: str) -> Path:
        path = reports_dir / filename
        # Serialize key metrics; full results omitted for size.
        data = {
            "config": report.config.name,
            "description": report.config.description,
            "total": report.total,
            "success_rate": report.success_rate,
            "infeasible_rate": report.infeasible_rate,
            "ratio_error_p50": report.ratio_error_p50,
            "ratio_error_p90": report.ratio_error_p90,
            "gap_p90": report.gap_p90,
            "elapsed_p95": report.elapsed_p95,
            "full_load_p50": report.full_load_p50,
            "worst_seeds": [
                {"seed": r.seed, "violations": r.violations_count, "error": r.error}
                for r in sorted(report.results, key=lambda r: r.violations_count, reverse=True)[:5]
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    return _write


def get_scenario(name: str):
    for s in SCENARIOS:
        if s.name == name:
            return s
    raise KeyError(f"unknown scenario: {name}")
