"""StaffChangeRecord domain model — onboard / leave / transfer events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

VALID_TYPES = frozenset({"onboard", "leave", "transfer"})


@dataclass(frozen=True)
class StaffChangeRecord:
    """A single staff change event.

    Attributes:
        person_id: The staff member this event applies to.
        date: Event effective date.
        type: One of 'onboard', 'leave', 'transfer'.
        job_type: Required for onboard; the staff member's job type string.
        business_line: Required for transfer; the new business line string.
                       Optional for onboard (may be None).
    """

    person_id: str
    date: date
    type: str
    job_type: str | None = None
    business_line: str | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.person_id:
            raise ValueError("person_id must not be empty")
        if self.type not in VALID_TYPES:
            raise ValueError(f"type must be one of {VALID_TYPES}, got '{self.type}'")
        if self.type == "onboard" and not self.job_type:
            raise ValueError("job_type is required for onboard records")
        if self.type == "transfer" and not self.business_line:
            raise ValueError("business_line is required for transfer records")
