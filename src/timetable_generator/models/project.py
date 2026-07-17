"""Project domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Project:
    """A project requiring work-hour investment.

    Attributes:
        id: Unique project identifier.
        name: Human-readable project name.
        start_date: Project start date (inclusive).
        end_date: Project end date (inclusive).
        target_ratio: Investment target as a ratio of total staff available hours (0.0–1.0).
        required_job_types: Set of job-type strings the project needs covered.
        associated_person_ids: Subset of staff IDs assigned to this project.
        ramp_up_point: Optional lifecycle warmup→full transition date.
        maintenance_point: Optional lifecycle full→maintenance transition date.
        business_line: Optional business line. May be None. Not used by MVP
            generation; kept for import/export round-trip fidelity.
    """

    id: str
    name: str
    start_date: date
    end_date: date
    target_ratio: float
    required_job_types: list[str]
    associated_person_ids: list[str]
    ramp_up_point: date | None = None
    maintenance_point: date | None = None
    business_line: str | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.id:
            raise ValueError("Project id must not be empty")
        if not (0.0 <= self.target_ratio <= 1.0):
            raise ValueError(f"target_ratio must be in [0, 1], got {self.target_ratio}")
        # required_job_types may be empty — means no job type constraint
        # associated_person_ids may be empty — means all staff (resolved at generation time)
        if self.end_date < self.start_date:
            raise ValueError(
                f"end_date ({self.end_date}) must not be before start_date ({self.start_date})"
            )
        if self.ramp_up_point is not None and not (
            self.start_date <= self.ramp_up_point <= self.end_date
        ):
            raise ValueError("ramp_up_point must be within [start_date, end_date]")
        if self.maintenance_point is not None and not (
            self.start_date <= self.maintenance_point <= self.end_date
        ):
            raise ValueError("maintenance_point must be within [start_date, end_date]")
        if (
            self.ramp_up_point
            and self.maintenance_point
            and self.ramp_up_point > self.maintenance_point
        ):
            raise ValueError("ramp_up_point must not be after maintenance_point")
