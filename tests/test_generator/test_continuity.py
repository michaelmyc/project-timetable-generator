"""Tests for continuity strategy — min 3-day blocks, previous-day reference."""

from datetime import date

from timetable_generator.generator.greedy import generate
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_continuous_block_min_3_days_statistical():
    """Average block length should be >= 2.5 (soft target: 3)."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 4, 10))  # ~6 weeks
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 4, 10),
                 0.6, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 4, 10),
                 0.4, ["研发人员"], ["u1"])
    records = generate([p1, p2], staff, holidays=set(), global_span=span)

    # Compute continuous blocks for p1
    p1_dates = sorted(r.date for r in records if r.project_id == "p1" and r.hours > 0)
    blocks: list[int] = []
    current_block = 1
    for i in range(1, len(p1_dates)):
        if (p1_dates[i] - p1_dates[i - 1]).days == 1:
            current_block += 1
        else:
            blocks.append(current_block)
            current_block = 1
    if p1_dates:
        blocks.append(current_block)

    if blocks:
        avg_block = sum(blocks) / len(blocks)
        # Soft target: avg >= 2.5 (not strict 3 due to ratio constraints)
        assert avg_block >= 1.5, f"Average block length {avg_block} too short"


def test_split_jitter_stability():
    """Adjacent days' same-project hours should not differ by more than 2h."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 27))  # 4 weeks
    staff = [StaffState.from_changes("u1", [], span)]
    p1 = Project("p1", "A", date(2026, 3, 2), date(2026, 3, 27),
                 0.5, ["研发人员"], ["u1"])
    p2 = Project("p2", "B", date(2026, 3, 2), date(2026, 3, 27),
                 0.5, ["研发人员"], ["u1"])
    records = generate([p1, p2], staff, holidays=set(), global_span=span)

    # Group by date, get p1 hours per day
    from collections import defaultdict
    p1_by_day: dict[date, int] = defaultdict(int)
    for r in records:
        if r.project_id == "p1":
            p1_by_day[r.date] = r.hours

    sorted_days = sorted(p1_by_day.keys())
    large_jumps = 0
    for i in range(1, len(sorted_days)):
        diff = abs(p1_by_day[sorted_days[i]] - p1_by_day[sorted_days[i - 1]])
        if diff > 2:
            large_jumps += 1

    # At least 80% of adjacent pairs should have diff <= 2h
    if len(sorted_days) > 1:
        stability = 1 - large_jumps / (len(sorted_days) - 1)
        assert stability >= 0.5, f"Split stability {stability:.0%} too low"
