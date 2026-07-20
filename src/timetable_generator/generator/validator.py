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


def _project_ratio_check(
    project: Project,
    records: list[WorkHourRecord],
    staff_states: list[StaffState],
    workdays: list[date],
    ratio_tolerance: float,
) -> tuple[float, Violation | None]:
    """Return (actual_ratio, violation?) using project-local capacity as denominator."""
    project_hours = sum(r.hours for r in records if r.project_id == project.id)
    local_cap = compute_project_local_capacity(project, staff_states, workdays)
    actual_ratio = project_hours / local_cap if local_cap > 0 else 0.0
    if abs(actual_ratio - project.target_ratio) > ratio_tolerance:
        return actual_ratio, Violation(
            rule="ratio_achievement",
            detail=f"Project {project.id}: target {project.target_ratio:.2%}, "
            f"actual {actual_ratio:.2%} (tolerance {ratio_tolerance:.2%})",
        )
    return actual_ratio, None


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

    # Check job type coverage (skip if project has no required job types)
    staff_by_id = {s.person_id: s for s in staff_states}
    for project in projects:
        if not project.required_job_types:
            continue  # No job type constraint → skip coverage check
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
