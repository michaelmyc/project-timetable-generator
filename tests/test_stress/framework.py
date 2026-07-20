"""Stress test framework — randomized input generation + quality aggregation.

Goal: validate greedy algorithm *quality* (not correctness) across many random
but legal inputs. Correctness is covered by unit/invariant tests; stress tests
answer "is the algorithm good enough in practice?"

Design:
- Fixed seed per case → reproducible.
- Input generator guarantees physical feasibility (quota <= local capacity)
  by construction (method B: derive ratio upper bound from overlap, sample below).
- No hypothesis dependency; hand-written generator.
- Quality gates enforced as assertions.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import date, timedelta

from timetable_generator.generator.capacity import compute_project_local_capacity, compute_workdays
from timetable_generator.generator.retry import generate_with_retry
from timetable_generator.generator.validator import validate
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan, StaffState


@dataclass
class StressConfig:
    """Parameter space for one stress scenario.

    Ranges are inclusive; the generator samples uniformly within them unless
    noted otherwise. ``overlap_tightness`` in [0,1] controls how much project
    intervals overlap with staff active spans (0 = wide overlap, 1 = minimal).
    """

    name: str
    description: str
    staff_count_range: tuple[int, int]
    project_count_range: tuple[int, int]
    span_days_range: tuple[int, int]
    overlap_tightness: float  # 0=wide, 1=tight
    ratio_range: tuple[float, float]
    # Staff onboard/leave churn: fraction of staff with non-default (non-full-span) active window.
    churn_rate: float = 0.0
    # Pool size per project: how many associated persons per project (min/max).
    pool_size_range: tuple[int, int] = (2, 5)
    # Job types to pick from.
    job_types: tuple[str, ...] = ("研发人员",)
    # Max cases to run in CI subset (full matrix runs more manually).
    ci_cases: int = 50
    full_cases: int = 300


@dataclass
class StressInput:
    """One concrete randomized input."""

    seed: int
    staff: list[StaffInfo]
    projects: list[Project]
    global_span: GlobalSpan
    holidays: set[date]

    def to_staff_states(self) -> list[StaffState]:
        return [StaffState.from_info(s, self.global_span) for s in self.staff]


@dataclass
class CaseResult:
    """Result of running one stress case."""

    seed: int
    success: bool
    infeasible: bool
    violations_count: int
    ratio_errors: list[float]  # |actual - target| per project
    gap_hours: dict[str, int]  # project_id -> unfilled hours (quota - actual)
    full_load_ratio: float
    elapsed_s: float
    total_records: int
    error: str | None = None


@dataclass
class StressReport:
    """Aggregated report across many cases."""

    config: StressConfig
    results: list[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.success) / len(self.results)

    @property
    def infeasible_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.infeasible) / len(self.results)

    def percentile(self, values: list[float], p: float) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        idx = min(len(s) - 1, max(0, int(len(s) * p)))
        return s[idx]

    @property
    def ratio_error_p50(self) -> float:
        return self.percentile([e for r in self.results for e in r.ratio_errors], 0.50)

    @property
    def ratio_error_p90(self) -> float:
        return self.percentile([e for r in self.results for e in r.ratio_errors], 0.90)

    @property
    def gap_p90(self) -> float:
        all_gaps = [g for r in self.results for g in r.gap_hours.values()]
        return self.percentile([float(g) for g in all_gaps], 0.90)

    @property
    def elapsed_p95(self) -> float:
        return self.percentile([r.elapsed_s for r in self.results], 0.95)

    @property
    def full_load_p50(self) -> float:
        return self.percentile([r.full_load_ratio for r in self.results], 0.50)

    def summary_lines(self) -> list[str]:
        return [
            f"  total={self.total}, success={self.success_rate:.1%}, infeasible={self.infeasible_rate:.1%}",
            f"  ratio_err P50={self.ratio_error_p50:.3f} P90={self.ratio_error_p90:.3f}",
            f"  gap P90={self.gap_p90:.0f}h, elapsed P95={self.elapsed_p95:.2f}s",
            f"  full_load P50={self.full_load_p50:.1%}",
        ]


def _gen_staff(
    rng: random.Random, span: GlobalSpan, count: int, churn_rate: float
) -> list[StaffInfo]:
    """Generate ``count`` staff with optional churn (non-full-span active windows)."""
    staff: list[StaffInfo] = []
    span_days = (span.end_date - span.start_date).days + 1
    for i in range(count):
        name = f"u{i + 1}"
        if rng.random() < churn_rate and span_days > 10:
            # Non-default: random onboard within first half, leave within second half
            onboard_offset = rng.randint(0, span_days // 2)
            leave_offset = rng.randint(span_days // 2, span_days - 1)
            onboard = span.start_date + timedelta(days=onboard_offset)
            leave = span.start_date + timedelta(days=leave_offset)
            staff.append(StaffInfo(name=name, onboard_date=onboard, leave_date=leave))
        else:
            staff.append(StaffInfo(name=name))
    return staff


def _gen_projects(
    rng: random.Random,
    span: GlobalSpan,
    staff: list[StaffInfo],
    count: int,
    config: StressConfig,
    workdays: list[date],
) -> list[Project]:
    """Generate ``count`` projects, guaranteeing physical feasibility by construction.

    Method B: for each project, pick associated persons + project interval, compute
    local capacity, then sample target_ratio capped so quota <= local_capacity * 0.95
    (leave 5% headroom to avoid boundary infeasibility).
    """
    projects: list[Project] = []
    span_days = (span.end_date - span.start_date).days + 1
    staff_ids = [s.name for s in staff]
    # All staff share the single job type in MVP; pick from config.job_types.
    job_type = config.job_types[0]

    for i in range(count):
        # Project interval: width depends on overlap_tightness (tight = shorter, less overlap)
        min_width = max(2, int(span_days * (1 - config.overlap_tightness) * 0.3))
        max_width = max(min_width + 1, int(span_days * (1 - config.overlap_tightness * 0.5)))
        width = rng.randint(min_width, max_width)
        start_offset = rng.randint(0, max(0, span_days - width))
        p_start = span.start_date + timedelta(days=start_offset)
        p_end = p_start + timedelta(days=width - 1)
        p_end = min(p_end, span.end_date)

        # Associated persons
        pool_min, pool_max = config.pool_size_range
        pool_size = min(len(staff_ids), rng.randint(pool_min, pool_max))
        associated = rng.sample(staff_ids, pool_size) if pool_size > 0 else []

        # Build a temporary StaffState list to compute local capacity
        states = [StaffState.from_info(s, span) for s in staff]
        # Temp project to measure local capacity
        probe = Project(
            id=f"probe_{i}",
            name=f"probe_{i}",
            start_date=p_start,
            end_date=p_end,
            target_ratio=1.0,
            required_job_types=[job_type],
            associated_person_ids=associated,
        )
        local_cap = compute_project_local_capacity(probe, states, workdays)
        if local_cap <= 0:
            # No overlap at all; skip this project (regenerate would bias the sample)
            # Use a trivial 0-ratio project so it doesn't bias stress results.
            projects.append(
                Project(
                    id=f"p{i + 1}",
                    name=f"P{i + 1}",
                    start_date=p_start,
                    end_date=p_end,
                    target_ratio=0.0,
                    required_job_types=[job_type],
                    associated_person_ids=associated,
                )
            )
            continue
        # Cap ratio so quota <= 0.95 * local_cap (feasibility headroom)
        ratio_max = min(config.ratio_range[1], 0.95)
        ratio_min = config.ratio_range[0]
        target_ratio = rng.uniform(ratio_min, ratio_max)
        projects.append(
            Project(
                id=f"p{i + 1}",
                name=f"P{i + 1}",
                start_date=p_start,
                end_date=p_end,
                target_ratio=round(target_ratio, 3),
                required_job_types=[job_type],
                associated_person_ids=associated,
            )
        )
    return projects


def generate_stress_input(seed: int, config: StressConfig) -> StressInput:
    """Generate one reproducible random input obeying ``config``."""
    rng = random.Random(seed)
    span_days = rng.randint(*config.span_days_range)
    start = date(2026, 1, 1) + timedelta(days=rng.randint(0, 30))
    end = start + timedelta(days=span_days - 1)
    span = GlobalSpan(start, end)

    staff_count = rng.randint(*config.staff_count_range)
    staff = _gen_staff(rng, span, staff_count, config.churn_rate)

    workdays = compute_workdays(span, set())
    project_count = rng.randint(*config.project_count_range)
    projects = _gen_projects(rng, span, staff, project_count, config, workdays)

    return StressInput(seed=seed, staff=staff, projects=projects, global_span=span, holidays=set())


def run_one_case(inp: StressInput) -> CaseResult:
    """Run generation + validation on one input, return metrics."""
    states = inp.to_staff_states()
    workdays = compute_workdays(inp.global_span, inp.holidays)
    t0 = time.perf_counter()
    try:
        result = generate_with_retry(inp.projects, states, inp.holidays, inp.global_span)
        records = result.records
    except Exception as e:
        return CaseResult(
            seed=inp.seed,
            success=False,
            infeasible=False,
            violations_count=0,
            ratio_errors=[],
            gap_hours={},
            full_load_ratio=0.0,
            elapsed_s=time.perf_counter() - t0,
            total_records=0,
            error=repr(e),
        )
    elapsed = time.perf_counter() - t0
    validation = validate(
        records, inp.projects, states, inp.holidays, inp.global_span, ratio_tolerance=0.08
    )
    # Per-project ratio errors and gaps
    ratio_errors: list[float] = []
    gap_hours: dict[str, int] = {}
    for p in inp.projects:
        local_cap = compute_project_local_capacity(p, states, workdays)
        quota = int(local_cap * p.target_ratio)
        actual = sum(r.hours for r in records if r.project_id == p.id)
        if quota > 0:
            ratio_errors.append(abs(actual - quota) / quota)
        gap_hours[p.id] = max(0, quota - actual)

    full_load = sum(1 for r in records if r.hours == 8) / len(records) if records else 0.0

    return CaseResult(
        seed=inp.seed,
        success=validation.is_valid,
        infeasible=False,
        violations_count=len(validation.violations),
        ratio_errors=ratio_errors,
        gap_hours=gap_hours,
        full_load_ratio=full_load,
        elapsed_s=elapsed,
        total_records=len(records),
    )


def run_stress(config: StressConfig, num_cases: int) -> StressReport:
    """Run ``num_cases`` random cases for ``config``, return aggregated report."""
    report = StressReport(config=config)
    for seed in range(num_cases):
        inp = generate_stress_input(seed, config)
        report.results.append(run_one_case(inp))
    return report
