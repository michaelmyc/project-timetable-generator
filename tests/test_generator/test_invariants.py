"""Invariant tests — properties that must hold for ANY generated schedule.

Unlike behavior tests (which check specific numbers), these verify structural
invariants: no holiday work, ≤8h/day, all records within staff active span and
project span. These catch regressions from algorithm changes.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date

from timetable_generator.generator.greedy import generate
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan, StaffState

FULL_DAY_HOURS = 8


def _make_random_input(seed: int) -> tuple[list[Project], list[StaffState], set[date], GlobalSpan]:
    """Generate a small random but legal input (physically feasible)."""
    rng = random.Random(seed)
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 27))
    n_staff = rng.randint(2, 5)
    staff_infos = []
    for i in range(n_staff):
        churn = rng.random() < 0.3
        if churn:
            ob = date(2026, 3, 2) + __import__("datetime").timedelta(days=rng.randint(0, 10))
            lv = date(2026, 3, 2) + __import__("datetime").timedelta(days=rng.randint(10, 25))
            staff_infos.append(StaffInfo(name=f"u{i + 1}", onboard_date=ob, leave_date=lv))
        else:
            staff_infos.append(StaffInfo(name=f"u{i + 1}"))
    states = [StaffState.from_info(s, span) for s in staff_infos]
    n_proj = rng.randint(1, 3)
    projects = []
    ids = [s.name for s in staff_infos]
    for j in range(n_proj):
        start = date(2026, 3, 2) + __import__("datetime").timedelta(days=rng.randint(0, 10))
        end = start + __import__("datetime").timedelta(days=rng.randint(5, 20))
        end = min(end, span.end_date)
        pool = rng.sample(ids, k=min(len(ids), rng.randint(1, 3)))
        projects.append(
            Project(f"p{j + 1}", f"P{j + 1}", start, end, rng.uniform(0.2, 0.5), ["研发人员"], pool)
        )
    return projects, states, set(), span


def _test_invariants(seed: int) -> None:
    projects, states, holidays, span = _make_random_input(seed)
    records = generate(projects, states, holidays, span)
    staff_by_id = {s.person_id: s for s in states}
    project_by_id = {p.id: p for p in projects}

    # Invariant 1: each record's hours in [1, 8]
    for r in records:
        assert 1 <= r.hours <= FULL_DAY_HOURS, f"seed={seed} record {r} hours out of [1,8]"

    # Invariant 2: no record on holiday
    for r in records:
        assert r.date not in holidays, f"seed={seed} record on holiday {r.date}"

    # Invariant 3: record date within staff active span
    for r in records:
        state = staff_by_id.get(r.person_id)
        assert state is not None, f"seed={seed} unknown person {r.person_id}"
        assert state.is_active_on(r.date), (
            f"seed={seed} record for {r.person_id} on {r.date} but not active"
        )

    # Invariant 4: record date within project span
    for r in records:
        proj = project_by_id.get(r.project_id)
        assert proj is not None, f"seed={seed} unknown project {r.project_id}"
        assert proj.start_date <= r.date <= proj.end_date, (
            f"seed={seed} record for {r.project_id} on {r.date} outside project span"
        )

    # Invariant 5: per-person per-day total ≤ 8h
    by_day: dict[tuple[str, date], int] = defaultdict(int)
    for r in records:
        by_day[(r.person_id, r.date)] += r.hours
    for (pid, d), total in by_day.items():
        assert total <= FULL_DAY_HOURS, f"seed={seed} {pid} on {d}: {total}h > 8h"


def test_invariants_20_random_inputs():
    """Run 20 random inputs, verify all invariants hold."""
    for seed in range(20):
        _test_invariants(seed)


def test_invariant_no_overselling_beyond_daily_capacity():
    """Explicitly: no person-day exceeds 8h, even with many projects sharing a person."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    states = [StaffState.from_info(StaffInfo(name="u1"), span)]
    # 3 projects all wanting u1 at 50% — daily total must still be ≤ 8h.
    projects = [
        Project(f"p{i}", f"P{i}", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"])
        for i in range(3)
    ]
    records = generate(projects, states, set(), span)
    by_day: dict[date, int] = defaultdict(int)
    for r in records:
        by_day[r.date] += r.hours
    for d, total in by_day.items():
        assert total <= 8, f"{d}: {total}h > 8h (3 projects overselling u1)"
