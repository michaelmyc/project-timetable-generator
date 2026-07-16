"""Compliance validator — checks generated records against hard constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from timetable_generator.generator.capacity import compute_capacity
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

    # Check job type coverage
    staff_by_id = {s.person_id: s for s in staff_states}
    for project in projects:
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

    # Compute ratio achievement
    total_capacity = compute_capacity(staff_states, holidays, global_span)
    ratio_achievement: dict[str, float] = {}
    for project in projects:
        project_hours = sum(r.hours for r in records if r.project_id == project.id)
        if total_capacity > 0:
            ratio_achievement[project.id] = project_hours / total_capacity
        else:
            ratio_achievement[project.id] = 0.0

        # Check ratio within tolerance
        actual_ratio = ratio_achievement[project.id]
        if abs(actual_ratio - project.target_ratio) > ratio_tolerance:
            violations.append(
                Violation(
                    rule="ratio_achievement",
                    detail=f"Project {project.id}: target {project.target_ratio:.2%}, "
                    f"actual {actual_ratio:.2%} (tolerance {ratio_tolerance:.2%})",
                )
            )

    is_valid = len(violations) == 0
    return ValidationResult(
        is_valid=is_valid,
        violations=violations,
        ratio_achievement=ratio_achievement,
    )
