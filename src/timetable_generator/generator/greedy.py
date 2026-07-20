"""Two-phase greedy generator.

Phase 1 (planner): produce per (project, person) commitments with a uniform
daily rate over the person's active∩project-span workdays. See planner.py.

Phase 2 (fill): honor commitments by walking each person's active workdays and
splitting the 8h/day capacity among all commitments covering that day in
proportion to their remaining target. This resolves day-level conflicts by
proportional sharing, eliminating first-come-first-served order dependence.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date

from timetable_generator.generator.capacity import compute_workdays
from timetable_generator.generator.planner import PersonProjectPlan, plan
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord

FULL_DAY_HOURS = 8
MIN_SPURT_DAYS = 3  # each continuous spurt >= 3 days (soft, not yet enforced)


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
    rng: random.Random | None = None,
) -> list[WorkHourRecord]:
    """Two-phase generation: plan commitments, then fill concrete hours."""
    if not projects:
        return []

    # Phase 1: plan. Raises InfeasibleProjectError if any project is physically impossible.
    plan_result = plan(projects, staff_states, holidays, global_span, rng)

    # Phase 2: fill concrete hours honoring commitments.
    workdays = compute_workdays(global_span, holidays)
    if not workdays:
        return []

    person_day_hours: dict[tuple[str, date], int] = defaultdict(int)
    records: list[WorkHourRecord] = []
    staff_by_id = {s.person_id: s for s in staff_states}

    # Group commitments by person.
    plans_by_person: dict[str, list[PersonProjectPlan]] = defaultdict(list)
    for pp in plan_result.plans:
        plans_by_person[pp.person_id].append(pp)

    # Per-commitment filled-so-far tracker.
    filled: dict[tuple[str, str], int] = defaultdict(int)

    for person_id, commitments in plans_by_person.items():
        state = staff_by_id.get(person_id)
        if state is None:
            continue
        # Index commitments by day. Count coverage to find "exclusive" days
        # (only one commitment covers that day) — those get full 8h for that
        # commitment without proportional sharing, so narrow-overlap commitments
        # with unique days aren't starved by shared-day competition.
        day_to_commitments: dict[date, list[PersonProjectPlan]] = defaultdict(list)
        for pp in commitments:
            for d in pp.overlap_days:
                day_to_commitments[d].append(pp)
        exclusive: dict[date, PersonProjectPlan] = {
            d: lst[0] for d, lst in day_to_commitments.items() if len(lst) == 1
        }
        # Active workdays for this person, in order.
        person_wds = sorted(wd for wd in workdays if state.is_active_on(wd))
        for wd in person_wds:
            avail = FULL_DAY_HOURS
            # Exclusive day → full capacity to the single covering commitment.
            excl = exclusive.get(wd)
            if excl is not None and filled[(excl.project_id, excl.person_id)] < excl.total:
                rem = excl.total - filled[(excl.project_id, excl.person_id)]
                h = min(avail, rem)
                if h > 0:
                    records.append(WorkHourRecord(excl.project_id, excl.person_id, wd, h))
                    person_day_hours[(person_id, wd)] += h
                    filled[(excl.project_id, excl.person_id)] += h
                    avail -= h
                if avail <= 0:
                    continue
            # Shared day (or exclusive commitment already filled) → proportional.
            active = [
                pp
                for pp in day_to_commitments.get(wd, [])
                if filled[(pp.project_id, pp.person_id)] < pp.total
            ]
            if not active:
                continue
            queue = list(active)
            queue.sort(key=lambda p: p.rate, reverse=True)
            while queue and avail > 0:
                total_rate = sum(p.rate for p in queue)
                if total_rate <= 0:
                    break
                pp = queue.pop(0)
                rem = pp.total - filled[(pp.project_id, pp.person_id)]
                if rem <= 0:
                    continue
                share = int(avail * pp.rate / total_rate)
                share = max(1, min(share, avail, rem))
                if share <= 0:
                    continue
                records.append(WorkHourRecord(pp.project_id, pp.person_id, wd, share))
                person_day_hours[(person_id, wd)] += share
                filled[(pp.project_id, pp.person_id)] += share
                avail -= share
            if avail > 0:
                leftover = [pp for pp in active if filled[(pp.project_id, pp.person_id)] < pp.total]
                leftover.sort(
                    key=lambda pp: pp.total - filled[(pp.project_id, pp.person_id)],
                    reverse=True,
                )
                for pp in leftover:
                    if avail <= 0:
                        break
                    rem = pp.total - filled[(pp.project_id, pp.person_id)]
                    give = min(1, avail, rem)
                    if give <= 0:
                        continue
                    records.append(WorkHourRecord(pp.project_id, pp.person_id, wd, give))
                    person_day_hours[(person_id, wd)] += give
                    filled[(pp.project_id, pp.person_id)] += give
                    avail -= give

    return records
