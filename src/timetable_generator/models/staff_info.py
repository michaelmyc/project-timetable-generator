"""StaffInfo domain model — user-editable staff profile for param import/export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DEFAULT_JOB_TYPE = "研发人员"


@dataclass(frozen=True)
class StaffInfo:
    """A staff member's editable profile.

    Attributes:
        name: Display name; also used as the staff id in MVP.
        job_type: Job-type string (e.g. "研发人员"). Defaults to DEFAULT_JOB_TYPE.
        business_line: Optional business line. May be None.
        annual_leave_days: Annual leave quota in days. Defaults to 0.
        onboard_date: Optional onboard (hire) date. May be None. Not used by MVP
            generation; kept for import/export round-trip fidelity.
        leave_date: Optional leave (termination) date. May be None. Not used by
            MVP generation; kept for import/export round-trip fidelity. When both
            onboard_date and leave_date are present, leave_date must be on or
            after onboard_date.
    """

    name: str
    job_type: str = DEFAULT_JOB_TYPE
    business_line: str | None = None
    annual_leave_days: int = 0
    onboard_date: date | None = None
    leave_date: date | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.job_type:
            raise ValueError("job_type must not be empty")
        if self.annual_leave_days < 0:
            raise ValueError(f"annual_leave_days must be >= 0, got {self.annual_leave_days}")
        if (
            self.onboard_date is not None
            and self.leave_date is not None
            and self.leave_date < self.onboard_date
        ):
            raise ValueError(
                f"leave_date ({self.leave_date}) must not be before "
                f"onboard_date ({self.onboard_date})"
            )

    @property
    def id(self) -> str:
        """Stable id — identical to name in MVP (FR-017 param reuse)."""
        return self.name
