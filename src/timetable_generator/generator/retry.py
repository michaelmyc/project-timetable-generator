"""N-retry orchestration — greedy construct → validate → retry (ADR-0009 D4)."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from timetable_generator.generator.greedy import generate_single
from timetable_generator.generator.validator import ValidationResult, validate
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord


class GenerationError(Exception):
    """Raised when generation fails after max retries."""

    def __init__(self, message: str, violations: list | None = None) -> None:
        super().__init__(message)
        self.violations = violations or []


@dataclass
class GenerationResult:
    """Result of a generation attempt with retry."""

    records: list[WorkHourRecord]
    validation: ValidationResult
    attempts: int


def generate_with_retry(
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set,
    global_span: GlobalSpan,
    greedy_fn: Callable | None = None,
    max_retries: int = 10,
    ratio_tolerance: float = 0.08,
    rng: random.Random | None = None,
) -> GenerationResult:
    """Generate with N retries: greedy → validate → retry until valid or exhausted.

    Args:
        projects: List of projects to generate for.
        staff_states: Staff states.
        holidays: Set of holiday dates.
        global_span: Global generation span.
        greedy_fn: Optional custom greedy function (for testing). If None, uses generate_single.
        max_retries: Maximum number of retry attempts.
        ratio_tolerance: Tolerance for ratio achievement validation.
        rng: Optional random number generator.

    Returns:
        GenerationResult with records and validation.

    Raises:
        GenerationError: If all retries fail.
    """
    if rng is None:
        rng = random.Random()

    fn = greedy_fn or generate_single

    last_result: ValidationResult | None = None
    for attempt in range(1, max_retries + 1):
        if greedy_fn is not None:
            records = fn(
                projects=projects,
                staff_states=staff_states,
                holidays=holidays,
                global_span=global_span,
            )
        else:
            records = fn(
                projects=projects,
                staff_states=staff_states,
                holidays=holidays,
                global_span=global_span,
                rng=rng,
            )

        result = validate(
            records,
            projects,
            staff_states,
            holidays,
            global_span,
            ratio_tolerance=ratio_tolerance,
        )
        last_result = result

        if result.is_valid:
            return GenerationResult(
                records=records,
                validation=result,
                attempts=attempt,
            )

    raise GenerationError(
        f"Generation failed after {max_retries} retries",
        violations=last_result.violations if last_result else [],
    )
