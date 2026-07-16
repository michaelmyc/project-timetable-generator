"""WorkHourRecord domain model — one person, one date, one project, hours."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WorkHourRecord:
    """A single work-hour record: one person's hours on one date for one project.

    Attributes:
        project_id: The project this work hour belongs to.
        person_id: The staff member who worked these hours.
        date: The work date.
        hours: Integer hours worked (0–8, 1h granularity).
    """

    project_id: str
    person_id: str
    date: date
    hours: int

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.project_id:
            raise ValueError("project_id must not be empty")
        if not self.person_id:
            raise ValueError("person_id must not be empty")
        if not isinstance(self.hours, int):
            raise ValueError(f"hours must be an integer, got {type(self.hours).__name__}")
        if not (0 <= self.hours <= 8):
            raise ValueError(f"hours must be in [0, 8], got {self.hours}")
