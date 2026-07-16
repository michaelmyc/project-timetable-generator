"""Tests for ratio conversion."""

from timetable_generator.generator.capacity import compute_target_hours


def test_target_hours_from_ratio():
    capacity = 1680  # total staff available hours
    ratio = 0.3
    target = compute_target_hours(capacity, ratio)
    assert target == 504  # 1680 * 0.3


def test_target_hours_full_ratio():
    assert compute_target_hours(800, 1.0) == 800


def test_target_hours_zero_ratio():
    assert compute_target_hours(800, 0.0) == 0


def test_target_hours_rounds_to_integer():
    """1h granularity: target hours should be integer."""
    # 40h capacity × 0.3 = 12h (exact)
    assert compute_target_hours(40, 0.3) == 12
    # 41h × 0.3 = 12.3 → rounds to 12
    assert compute_target_hours(41, 0.3) == 12
