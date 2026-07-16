"""Judge function — multi-dimensional scoring of generated records."""

from __future__ import annotations

from dataclasses import dataclass

from timetable_generator.generator.validator import ValidationResult
from timetable_generator.models.work_hour import WorkHourRecord


@dataclass
class JudgeScore:
    """Multi-dimensional score for a single evaluation case."""

    ratio_accuracy: float  # 1 - |actual_ratio - target_ratio| / target_ratio (0-1)
    hard_constraint_pass: bool  # All hard constraints passed
    full_load_ratio: float  # Fraction of records with hours == 8
    jitter_naturalness: float  # Randomness of day selection (0=mechanical, 1=natural)
    retry_count: int  # Number of retries (fewer is better)
    overall_score: float  # Weighted combination


def judge(
    records: list[WorkHourRecord],
    validation: ValidationResult,
    target_ratio: float,
    actual_ratio: float,
    retry_count: int,
) -> JudgeScore:
    """Judge a generation result across multiple dimensions.

    Args:
        records: Generated work-hour records.
        validation: Validation result (hard constraints).
        target_ratio: The project's target ratio.
        actual_ratio: The achieved ratio.
        retry_count: Number of retries used.

    Returns:
        JudgeScore with multi-dimensional metrics.
    """
    # Ratio accuracy: how close actual is to target
    if target_ratio > 0:
        ratio_accuracy = 1.0 - min(1.0, abs(actual_ratio - target_ratio) / target_ratio)
    else:
        ratio_accuracy = 1.0 if actual_ratio == 0 else 0.0

    hard_pass = validation.is_valid

    # Full load ratio: fraction of records with 8h
    full_load = sum(1 for r in records if r.hours == 8) / len(records) if records else 0.0

    # Jitter naturalness: check if assigned days are not purely sequential
    # We measure how "spread out" the assigned days are vs purely sequential
    if len(records) > 2:
        dates = sorted(r.date for r in records)
        # Count gaps (non-consecutive) — more gaps = more natural spread
        gaps = sum(1 for i in range(1, len(dates)) if (dates[i] - dates[i - 1]).days > 1)
        # Normalize: 0 gaps = fully sequential (mechanical), many gaps = spread (natural)
        max_possible_gaps = len(dates) - 1
        jitter_naturalness = gaps / max_possible_gaps if max_possible_gaps > 0 else 1.0
    else:
        jitter_naturalness = 1.0  # Trivially natural for small cases

    # Overall score: weighted combination
    # Hard constraint is a gate (0 if failed)
    if not hard_pass:
        overall = 0.0
    else:
        overall = (
            0.40 * ratio_accuracy
            + 0.25 * full_load
            + 0.20 * jitter_naturalness
            + 0.15 * (1.0 / max(1, retry_count))  # fewer retries = better
        )

    return JudgeScore(
        ratio_accuracy=ratio_accuracy,
        hard_constraint_pass=hard_pass,
        full_load_ratio=full_load,
        jitter_naturalness=jitter_naturalness,
        retry_count=retry_count,
        overall_score=overall,
    )
