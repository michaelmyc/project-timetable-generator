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

from __future__ import annotations

import math
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
) -> PlanResult:
    """Run phase 1: produce commitments for each (project, person)."""
    workdays = compute_workdays(global_span, holidays)
    by_id = {s.person_id: s for s in staff_states}

    result = PlanResult()

    # Precompute local capacity + quota + tension for ordering.
    project_meta: list[tuple[Project, int, int, float]] = []
    for p in projects:
        local_cap = compute_project_local_capacity(p, staff_states, workdays)
        quota = int(local_cap * p.target_ratio)
        if quota > local_cap and local_cap > 0:
            raise InfeasibleProjectError(p.id, quota, local_cap)
        if local_cap == 0 and quota > 0:
            raise InfeasibleProjectError(p.id, quota, local_cap)
        result.quotas[p.id] = quota
        result.local_capacities[p.id] = local_cap
        project_meta.append((p, quota, local_cap, _project_tension(p, quota, local_cap)))

    # Toughest first (higher tension = quota close to capacity).
    project_meta.sort(key=lambda t: t[3], reverse=True)

    # All commitments so far (used to compute remaining theoretical capacity).
    all_commitments: list[PersonProjectPlan] = []

    for project, quota, _local_cap, _tension in project_meta:
        if quota <= 0:
            result.gaps[project.id] = 0
            continue

        # Candidate persons: associated, with non-empty overlap, sorted by remaining
        # *theoretical* capacity on this project's overlap (most remaining first).
        candidates: list[tuple[str, list[date], int]] = []
        for pid in project.associated_person_ids:
            state = by_id.get(pid)
            if state is None:
                continue
            ov = _overlap_days(state, project, workdays)
            if not ov:
                continue
            remaining_cap = _remaining_theoretical_capacity(pid, ov, all_commitments)
            if remaining_cap <= 0:
                continue
            candidates.append((pid, ov, remaining_cap))

        if not candidates:
            result.gaps[project.id] = quota
            continue

        # Target headcount: theoretical minimum overshot by factor.
        m_days = max(1, (project.end_date - project.start_date).days + 1)
        min_persons = max(1, math.ceil(quota / (m_days * FULL_DAY_HOURS)))
        target_count = max(min_persons, math.ceil(min_persons * TARGET_PERSONS_OVERSHOOT))

        candidates.sort(key=lambda c: c[2], reverse=True)

        remaining_quota = quota
        planned_for_project: list[PersonProjectPlan] = []

        # First pass: allocate to the top target_count persons by overlap proportion.
        chosen = candidates[:target_count]
        total_overlap = sum(len(ov) for _, ov, _ in chosen) or 1

        for pid, ov, _rem in chosen:
            if remaining_quota <= 0:
                break
            share = int(remaining_quota * (len(ov) / total_overlap))
            # Bound by this person's remaining theoretical capacity on overlap.
            rem_cap = _remaining_theoretical_capacity(
                pid, ov, all_commitments + planned_for_project
            )
            share = min(share, rem_cap)
            if share <= 0:
                continue
            rate = min(MAX_UNIFORM_RATE, share / len(ov))
            total = int(rate * len(ov))
            if total <= 0:
                continue
            plan_item = PersonProjectPlan(
                person_id=pid,
                project_id=project.id,
                overlap_days=list(ov),
                rate=rate,
                total=total,
            )
            planned_for_project.append(plan_item)
            all_commitments.append(plan_item)
            remaining_quota -= total

        # Second pass: residual quota spread across any candidate with remaining
        # theoretical capacity (re-using already-planned persons allowed).
        if remaining_quota > 0:
            for pid, ov, _rem in candidates:
                if remaining_quota <= 0:
                    break
                rem_cap = _remaining_theoretical_capacity(pid, ov, all_commitments)
                if rem_cap <= 0:
                    continue
                extra = min(remaining_quota, rem_cap)
                rate = min(MAX_UNIFORM_RATE, extra / len(ov))
                total = int(rate * len(ov))
                if total <= 0:
                    continue
                existing = next((pp for pp in planned_for_project if pp.person_id == pid), None)
                if existing is not None:
                    existing.total += total
                    existing.rate = existing.total / len(existing.overlap_days)
                    all_commitments.append(
                        PersonProjectPlan(
                            person_id=pid,
                            project_id=project.id,
                            overlap_days=list(ov),
                            rate=rate,
                            total=total,
                        )
                    )
                else:
                    plan_item = PersonProjectPlan(
                        person_id=pid,
                        project_id=project.id,
                        overlap_days=list(ov),
                        rate=rate,
                        total=total,
                    )
                    planned_for_project.append(plan_item)
                    all_commitments.append(plan_item)
                remaining_quota -= total

        result.plans.extend(planned_for_project)
        result.gaps[project.id] = max(0, remaining_quota)

    return result
