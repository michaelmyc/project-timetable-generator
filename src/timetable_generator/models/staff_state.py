"""GlobalSpan and StaffState — staff active-span derivation with default fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from timetable_generator.models.staff_change import StaffChangeRecord

DEFAULT_JOB_TYPE = "研发人员"


@dataclass(frozen=True)
class GlobalSpan:
    """The global generation time range for a session."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError(
                f"end_date ({self.end_date}) must not be before start_date ({self.start_date})"
            )

    def contains(self, d: date) -> bool:
        """Check if a date falls within this span (inclusive)."""
        return self.start_date <= d <= self.end_date


@dataclass
class StaffState:
    """Derived state of a staff member: active span, job type, business line segments.

    Built from StaffChangeRecord sequence or default fallback (ADR-0007).

    active_span semantics:
    - start = onboard date (inclusive, staff is active on this date)
    - end = leave date (exclusive, staff is NOT active on this date) OR global_end (inclusive)
    """

    person_id: str
    active_span: tuple[date, date]
    job_type: str
    business_line: str | None
    business_line_segments: list[tuple[date, str | None]] = field(default_factory=list)
    _end_is_leave: bool = False

    @classmethod
    def from_changes(
        cls,
        person_id: str,
        changes: list[StaffChangeRecord],
        global_span: GlobalSpan,
    ) -> StaffState:
        """Build StaffState from change records, with default fallback if no changes."""
        if not changes:
            return cls(
                person_id=person_id,
                active_span=(global_span.start_date, global_span.end_date),
                job_type=DEFAULT_JOB_TYPE,
                business_line=None,
                business_line_segments=[(global_span.start_date, None)],
                _end_is_leave=False,
            )

        sorted_changes = sorted(changes, key=lambda c: c.date)

        onboard = next((c for c in sorted_changes if c.type == "onboard"), None)
        leave = next((c for c in sorted_changes if c.type == "leave"), None)

        if onboard is None:
            return cls(
                person_id=person_id,
                active_span=(global_span.start_date, global_span.end_date),
                job_type=DEFAULT_JOB_TYPE,
                business_line=None,
                business_line_segments=[(global_span.start_date, None)],
                _end_is_leave=False,
            )

        active_start = onboard.date
        if leave:
            active_end = leave.date
            end_is_leave = True
        else:
            active_end = global_span.end_date
            end_is_leave = False

        # Build business line segments from onboard + transfers
        bl_changes = [c for c in sorted_changes if c.type in ("onboard", "transfer")]
        segments: list[tuple[date, str | None]] = []
        for c in bl_changes:
            segments.append((c.date, c.business_line))

        current_bl = segments[-1][1] if segments else None

        return cls(
            person_id=person_id,
            active_span=(active_start, active_end),
            job_type=onboard.job_type or DEFAULT_JOB_TYPE,
            business_line=current_bl,
            business_line_segments=segments,
            _end_is_leave=end_is_leave,
        )

    def is_active_on(self, d: date) -> bool:
        """Check if staff is active on a given date.

        - If end is a leave date: active on [start, end) — end is exclusive.
        - If end is global_end: active on [start, end] — end is inclusive.
        """
        start, end = self.active_span
        if self._end_is_leave:
            return start <= d < end
        else:
            return start <= d <= end

    def business_line_at(self, d: date) -> str | None:
        """Get business line at a specific date."""
        result: str | None = None
        for seg_start, bl in self.business_line_segments:
            if d >= seg_start:
                result = bl
            else:
                break
        return result
