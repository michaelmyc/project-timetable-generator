"""Phase 1 planner — project-person commitment with uniform daily rate.

Phase 1 is a *rough estimate*, not a precise allocation. For each (project,
person) it commits a total hours figure and a uniform daily rate over the
person's overlap days. Commitments are bounded by *theoretical* capacity
(overlap × 8h minus already-committed rate on overlapping days), not by a hard
daily-availability pool. This lets phase 1 over-commit on a given day (local
overshoot); phase 2 (greedy.fill) absorbs the overshoot by placing concrete
hours on whatever active days still have room.

This matches the design intent: a rough plan that avoids one project hoarding
a person, with residual conflicts resolved at fill time.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import date

from timetable_generator.generator.capacity import (
    compute_project_local_capacity,
    compute_workdays,
)
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState

FULL_DAY_HOURS = 8
# Overshoot factor: target more persons than the theoretical minimum so a single
# person isn't locked into one project. 1.5 = plan for 50% more headcount.
TARGET_PERSONS_OVERSHOOT = 1.5
# Soft cap on uniform daily rate per (project, person). Keeps a person from
# being monopolized by one project in phase 1, leaving room for later projects.
MAX_UNIFORM_RATE = 6.0


@dataclass
class PersonProjectPlan:
    """One (project, person) commitment from the planner."""

    person_id: str
    project_id: str
    overlap_days: list[date]
    rate: float  # uniform h/day the planner assumes this person spends on this project
    total: int  # committed total hours (rate × len(overlap_days), rounded)


@dataclass
class PlanResult:
    """Output of phase 1."""

    plans: list[PersonProjectPlan] = field(default_factory=list)
    # Per-project unfilled quota (quota − Σ committed totals). Non-zero means
    # phase 2 likely can't reach the target ratio for that project.
    gaps: dict[str, int] = field(default_factory=dict)
    # Per-project quota (for phase 2 / diagnostics).
    quotas: dict[str, int] = field(default_factory=dict)
    # Per-project local capacity (denominator used for ratio).
    local_capacities: dict[str, int] = field(default_factory=dict)


class InfeasibleProjectError(ValueError):
    """Raised when a project's quota exceeds its physical local capacity."""

    def __init__(self, project_id: str, quota: int, local_capacity: int) -> None:
        super().__init__(
            f"项目 {project_id} 配额 {quota}h 超过物理上限 {local_capacity}h "
            f"（关联员工在项目区间内可用工时不足）。请降低 target_ratio 或增加关联员工。"
        )
        self.project_id = project_id
        self.quota = quota
        self.local_capacity = local_capacity


class OvercommitError(ValueError):
    """Raised when a person is overcommitted on one or more days (Σ ratio > 1.0)."""

    def __init__(self, person_id: str, day: date, total_ratio: float, projects: list[str]) -> None:
        super().__init__(
            f"人员 {person_id} 在 {day} 被过度分配：关联项目 {projects} 的 ratio 之和 = "
            f"{total_ratio:.0%}，超过 100%。请降低部分项目的 target_ratio 或增加关联员工。"
        )
        self.person_id = person_id
        self.day = day
        self.total_ratio = total_ratio
        self.projects = projects


class ProjectTotalRatioError(ValueError):
    """Raised when the sum of all projects' target_ratio exceeds 1.0."""

    def __init__(self, total_ratio: float) -> None:
        super().__init__(
            f"所有项目的投入比例之和 = {total_ratio:.0%}，超过 100%。"
            f"请降低部分项目的 target_ratio。"
        )
        self.total_ratio = total_ratio


def _overlap_days(state: StaffState, project: Project, workdays: list[date]) -> list[date]:
    return [
        wd
        for wd in workdays
        if project.start_date <= wd <= project.end_date and state.is_active_on(wd)
    ]


def _project_tension(project: Project, quota: int, local_capacity: int) -> float:
    """How tight a project is: quota / local_capacity. Higher = fill first."""
    if local_capacity <= 0:
        return math.inf
    return quota / local_capacity


def _remaining_theoretical_capacity(
    person_id: str,
    overlap: list[date],
    commitments: list[PersonProjectPlan],
) -> int:
    """Theoretical remaining hours this person could still commit on ``overlap``.

    = Σ_{d in overlap} (8 − Σ rate of prior commitments whose overlap covers d).
    Prior commitments on non-overlapping days don't reduce this. This is the
    *rough* capacity bound for phase 1; it may still overshoot on a single day,
    which phase 2 absorbs.
    """
    overlap_set = set(overlap)
    used_by_day: dict[date, float] = {}
    for pp in commitments:
        if pp.person_id != person_id:
            continue
        for d in pp.overlap_days:
            if d in overlap_set:
                used_by_day[d] = used_by_day.get(d, 0.0) + pp.rate
    remaining = 0
    for d in overlap:
        remaining += max(0, FULL_DAY_HOURS - used_by_day.get(d, 0.0))
    return int(remaining)


def plan(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,
) -> PlanResult:
    """Run phase 1: produce commitments for each (project, person).

    Strategy Q: per-project quota is split among associated persons in proportion
    to each person's overlap days. No sequential capacity deduction — each person
    gets their share independently. This eliminates ordering dependence: no
    project "goes first" to monopolize a person.

    Overcommit (one person on many high-ratio projects) degrades gracefully —
    each project gets its proportional share of that person, fill resolves the
    daily 8h split.

    ``rng`` (optional) shuffles project order for retry diversity (affects which
    projects get slightly more due to int rounding, but no structural advantage).
    """
    workdays = compute_workdays(global_span, holidays)
    by_id = {s.person_id: s for s in staff_states}

    result = PlanResult()

    # Precompute local capacity + quota. Physical infeasibility check.
    for p in projects:
        local_cap = compute_project_local_capacity(p, staff_states, workdays)
        quota = int(local_cap * p.target_ratio)
        if quota > local_cap and local_cap > 0:
            raise InfeasibleProjectError(p.id, quota, local_cap)
        if local_cap == 0 and quota > 0:
            raise InfeasibleProjectError(p.id, quota, local_cap)
        result.quotas[p.id] = quota
        result.local_capacities[p.id] = local_cap
    # Person-day overcommit is NOT checked here — it's a resource scarcity
    # situation, not a config error. The generator handles it by distributing
    # 8h proportionally among covering projects.
    # Process projects (order only affects int-rounding distribution, not
    # structural allocation — every person gets their overlap-proportional share).
    project_list = list(projects)
    if rng:
        rng.shuffle(project_list)

    for project in project_list:
        quota = result.quotas.get(project.id, 0)
        if quota <= 0:
            result.gaps[project.id] = 0
            continue

        # Compute each associated person's overlap with this project.
        person_overlaps: list[tuple[str, list[date]]] = []
        total_overlap = 0
        for pid in project.associated_person_ids:
            state = by_id.get(pid)
            if state is None:
                continue
            ov = _overlap_days(state, project, workdays)
            if not ov:
                continue
            person_overlaps.append((pid, ov))
            total_overlap += len(ov)

        if not person_overlaps or total_overlap == 0:
            result.gaps[project.id] = quota
            continue

        # Split quota by overlap proportion. Each person gets an independent
        # share — no deduction of other projects' commitments.
        committed = 0
        for pid, ov in person_overlaps:
            share = int(quota * len(ov) / total_overlap)
            if share <= 0:
                continue
            rate = share / len(ov)
            total = int(rate * len(ov))
            if total <= 0:
                continue
            result.plans.append(
                PersonProjectPlan(
                    person_id=pid,
                    project_id=project.id,
                    overlap_days=list(ov),
                    rate=rate,
                    total=total,
                )
            )
            committed += total

        result.gaps[project.id] = max(0, quota - committed)

    return result
