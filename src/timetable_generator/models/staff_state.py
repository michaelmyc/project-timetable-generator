"""GlobalSpan and StaffState — staff active-span derivation with default fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from timetable_generator.models.staff_change import StaffChangeRecord
from timetable_generator.models.staff_info import StaffInfo

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

    @classmethod
    def from_info(cls, info: StaffInfo, global_span: GlobalSpan) -> StaffState:
        """Build StaffState from a StaffInfo profile (MVP path, no change records).

        - onboard_date None → defaults to global_span.start (inclusive).
        - leave_date None → defaults to global_span.end (inclusive), _end_is_leave=False.
        - leave_date present → treated as *last active day* (inclusive); StaffState
          uses exclusive end semantics internally, so end = leave_date + 1 day.
        - Clamps to global_span. A staff fully outside the span gets a degenerate
          active_span (end <= start) so is_active_on returns False for any span day.
        - If leave_date is beyond span end, it's clamped and _end_is_leave set False
          (the staff is effectively active through the whole span).
        """
        start = info.onboard_date or global_span.start_date
        if info.leave_date is not None:
            raw_end = info.leave_date + timedelta(days=1)
            end_is_leave = True
        else:
            raw_end = global_span.end_date + timedelta(days=1)
            end_is_leave = False
        # Clamp to span.
        start = max(start, global_span.start_date)
        end = min(raw_end, global_span.end_date + timedelta(days=1))
        # If the leave boundary was clamped (was beyond span), it's no longer a real
        # leave within this span — treat as inclusive span end.
        if end_is_leave and raw_end > global_span.end_date + timedelta(days=1):
            end_is_leave = False
        return cls(
            person_id=info.id,
            active_span=(start, end),
            job_type=info.job_type,
            business_line=info.business_line,
            business_line_segments=[(start, info.business_line)],
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
