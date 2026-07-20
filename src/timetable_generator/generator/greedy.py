"""Single-phase online greedy generator.

No separate planner/fill phases. For each person, walk their active workdays in
order. On each day, split the 8h capacity among all projects that (a) the person
is associated with and (b) cover this day, in proportion to each project's
*remaining quota* (quota − hours already filled across all days so far).

This is an online algorithm: the daily split adapts to how much each project
still needs. A project that has already received most of its quota gets a
smaller share; a project that is far from its quota gets a larger share. The
total naturally converges toward each project's quota without a pre-computed
fixed commitment.

Physical infeasibility (project quota > local capacity, or total Σratio > 1.0)
is checked upfront. Person-day overcommit (one person on many high-ratio
projects) is NOT an error — the algorithm distributes 8h proportionally, and
projects simply get less than their target ratio (resource scarcity, not error).
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date

from timetable_generator.generator.capacity import (
    compute_project_local_capacity,
    compute_workdays,
)
from timetable_generator.generator.planner import InfeasibleProjectError, ProjectTotalRatioError
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord

FULL_DAY_HOURS = 8


def generate_single(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,  # noqa: ARG001 — kept for backward compat
) -> list[WorkHourRecord]:
    """Backward compat — delegates to generate()."""
    return generate(projects, staff_states, holidays, global_span)


def generate(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    rng: random.Random | None = None,  # noqa: ARG001 — kept for backward compat
) -> list[WorkHourRecord]:
    """Generate work-hour records by per-person per-day online proportional split.

    No pre-computed commitments. Each day, 8h is split by remaining quota.
    """
    if not projects:
        return []

    workdays = compute_workdays(global_span, holidays)
    if not workdays:
        return []

    # --- Upfront feasibility checks ---
    # 1. Project total ratio > 1.0 → user config error.
    total_ratio = sum(p.target_ratio for p in projects)
    if total_ratio > 1.0 + 1e-9:
        raise ProjectTotalRatioError(total_ratio)

    # 2. Per-project physical infeasibility (quota > local capacity).
    quotas: dict[str, int] = {}
    for p in projects:
        local_cap = compute_project_local_capacity(p, staff_states, workdays)
        quota = int(local_cap * p.target_ratio)
        if quota > local_cap and local_cap > 0:
            raise InfeasibleProjectError(p.id, quota, local_cap)
        if local_cap == 0 and quota > 0:
            raise InfeasibleProjectError(p.id, quota, local_cap)
        quotas[p.id] = quota

    staff_by_id = {s.person_id: s for s in staff_states}
    project_by_id = {p.id: p for p in projects}

    # Track filled hours per project (across all persons, all days).
    project_filled: dict[str, int] = defaultdict(int)
    records: list[WorkHourRecord] = []

    # Index: person_id → date → list of project_ids covering that day.
    person_day_projects: dict[str, dict[date, list[str]]] = defaultdict(lambda: defaultdict(list))
    for project in projects:
        for pid in project.associated_person_ids:
            state = staff_by_id.get(pid)
            if state is None:
                continue
            for wd in workdays:
                if project.start_date <= wd <= project.end_date and state.is_active_on(wd):
                    person_day_projects[pid][wd].append(project.id)

    # Walk each person's active workdays in order.
    # Process persons in rng-shuffled order for retry diversity.
    person_ids = list(person_day_projects.keys())
    if rng:
        rng.shuffle(person_ids)

    for person_id in person_ids:
        day_map = person_day_projects[person_id]
        for wd in sorted(day_map):
            covering_pids = day_map[wd]
            if not covering_pids:
                continue

            # Compute remaining quota for each covering project.
            remaining: list[tuple[str, int]] = []
            for pid in covering_pids:
                rem = quotas[pid] - project_filled[pid]
                if rem > 0:
                    remaining.append((pid, rem))

            if not remaining:
                continue

            avail = FULL_DAY_HOURS

            # Single project covers this day → give it all 8h (capped by remaining).
            if len(remaining) == 1:
                pid, rem = remaining[0]
                h = min(avail, rem)
                if h > 0:
                    records.append(WorkHourRecord(pid, person_id, wd, h))
                    project_filled[pid] += h
                continue

            # Multiple projects: split 8h by remaining quota proportion.
            total_remaining = sum(rem for _, rem in remaining)
            # Sort by remaining desc (largest gap first) with rng jitter for diversity.
            remaining.sort(key=lambda x: x[1] + (rng.random() if rng else 0), reverse=True)

            for pid, rem in remaining:
                if avail <= 0:
                    break
                share = int(FULL_DAY_HOURS * rem / total_remaining)
                share = max(1, min(share, avail, rem))
                if share <= 0:
                    continue
                records.append(WorkHourRecord(pid, person_id, wd, share))
                project_filled[pid] += share
                avail -= share

            # Leftover from int truncation → give to largest remaining.
            if avail > 0:
                # Recompute remaining (some may have been filled).
                still_needy = [
                    (pid, quotas[pid] - project_filled[pid])
                    for pid in covering_pids
                    if quotas[pid] - project_filled[pid] > 0
                ]
                still_needy.sort(key=lambda x: x[1], reverse=True)
                for pid, rem in still_needy:
                    if avail <= 0:
                        break
                    give = min(avail, rem)
                    if give <= 0:
                        continue
                    records.append(WorkHourRecord(pid, person_id, wd, give))
                    project_filled[pid] += give
                    avail -= give

    return records
