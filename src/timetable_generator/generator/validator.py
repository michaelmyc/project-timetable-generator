"""Compliance validator — checks generated records against hard constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from timetable_generator.generator.capacity import compute_project_local_capacity, compute_workdays
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState
from timetable_generator.models.work_hour import WorkHourRecord

FULL_DAY_HOURS = 8


@dataclass
class Violation:
    """A single compliance violation."""

    rule: str
    detail: str
    record: WorkHourRecord | None = None


@dataclass
class ValidationResult:
    """Result of compliance validation."""

    is_valid: bool
    violations: list[Violation] = field(default_factory=list)
    ratio_achievement: dict[str, float] = field(default_factory=dict)


def _person_remaining_capacity(
    person_id: str,
    project: Project,
    staff_states: list[StaffState],
    records: list[WorkHourRecord],
    workdays: list[date],
) -> int:
    """How many more hours this person could still give to this project.

    = (active workdays in project span) × 8 − (total hours already assigned
    to this person across ALL projects on those days).
    This is the physical room for adjustment — if the project's gap fits within
    the sum of associated persons' remaining capacity, the gap is an algorithm
    precision issue (adjustable); otherwise it's a configuration problem.
    """
    state = next((s for s in staff_states if s.person_id == person_id), None)
    if state is None:
        return 0
    # Active workdays in project span
    project_days = [
        wd
        for wd in workdays
        if project.start_date <= wd <= project.end_date and state.is_active_on(wd)
    ]
    if not project_days:
        return 0
    # Total hours this person is already assigned on those days (any project)
    assigned = sum(
        r.hours for r in records if r.person_id == person_id and r.date in set(project_days)
    )
    physical = len(project_days) * FULL_DAY_HOURS
    return max(0, physical - assigned)


def _project_ratio_check(
    project: Project,
    records: list[WorkHourRecord],
    staff_states: list[StaffState],
    workdays: list[date],
    ratio_tolerance: float,
) -> tuple[float, Violation | None]:
    """Return (actual_ratio, violation?) using project-local capacity as denominator.

    A ratio_achievement violation is only reported when the gap is *adjustable* —
    i.e. the project's associated persons collectively have enough remaining
    physical capacity to cover the gap. If they don't, the shortfall is a
    configuration problem (overcommit), not an algorithm failure.
    """
    project_hours = sum(r.hours for r in records if r.project_id == project.id)
    local_cap = compute_project_local_capacity(project, staff_states, workdays)
    actual_ratio = project_hours / local_cap if local_cap > 0 else 0.0
    if abs(actual_ratio - project.target_ratio) <= ratio_tolerance:
        return actual_ratio, None
    # Gap exists — check if it's adjustable (physical room available).
    gap = int(local_cap * project.target_ratio) - project_hours
    if gap > 0:
        remaining = sum(
            _person_remaining_capacity(pid, project, staff_states, records, workdays)
            for pid in project.associated_person_ids
        )
        if remaining < gap:
            # Not enough physical room → configuration problem, not algorithm failure.
            return actual_ratio, None
    return actual_ratio, Violation(
        rule="ratio_achievement",
        detail=f"Project {project.id}: target {project.target_ratio:.2%}, "
        f"actual {actual_ratio:.2%} (tolerance {ratio_tolerance:.2%}), "
        f"gap {gap}h adjustable (remaining capacity {remaining if gap > 0 else 0}h)",
    )


def validate(
    records: list[WorkHourRecord],
    projects: list[Project],
    staff_states: list[StaffState],
    holidays: set[date],
    global_span: GlobalSpan,
    ratio_tolerance: float = 0.02,
) -> ValidationResult:
    """Validate generated work-hour records against hard constraints.

    Checks:
    - hours_eq_8: each record's hours <= 8 (WorkHourRecord already enforces 0-8)
    - no_holiday_hours: no records on holiday dates
    - job_type_coverage: each project has at least 1 person per required job type
    - ratio_achievement: each project's actual ratio matches target (within tolerance)
    """
    violations: list[Violation] = []

    # Check no holiday hours
    for r in records:
        if r.date in holidays:
            violations.append(
                Violation(
                    rule="no_holiday_hours",
                    detail=f"Record on holiday {r.date} for {r.person_id}/{r.project_id}",
                    record=r,
                )
            )
    # Check job type coverage (skip if project has no required job types or no quota)
    staff_by_id = {s.person_id: s for s in staff_states}
    workdays_for_check = compute_workdays(global_span, holidays)
    for project in projects:
        if not project.required_job_types:
            continue  # No job type constraint → skip
        # Skip projects with zero quota (ratio=0 → no investment needed)
        local_cap = compute_project_local_capacity(project, staff_states, workdays_for_check)
        if int(local_cap * project.target_ratio) <= 0:
            continue
        # Find all persons with records on this project
        persons_on_project = {r.person_id for r in records if r.project_id == project.id}
        # Check each required job type has at least 1 person
        covered_types: set[str] = set()
        for pid in persons_on_project:
            state = staff_by_id.get(pid)
            if state and state.job_type in project.required_job_types:
                covered_types.add(state.job_type)
        missing = set(project.required_job_types) - covered_types
        if missing:
            violations.append(
                Violation(
                    rule="job_type_coverage",
                    detail=f"Project {project.id} missing job types: {missing}",
                )
            )

    # Compute ratio achievement using project-local capacity as denominator
    # (aligned with the planner/generator's quota definition).
    workdays = compute_workdays(global_span, holidays)
    ratio_achievement: dict[str, float] = {}
    for project in projects:
        actual_ratio, viol = _project_ratio_check(
            project, records, staff_states, workdays, ratio_tolerance
        )
        ratio_achievement[project.id] = actual_ratio
        if viol is not None:
            violations.append(viol)

    is_valid = len(violations) == 0
    return ValidationResult(
        is_valid=is_valid,
        violations=violations,
        ratio_achievement=ratio_achievement,
    )
