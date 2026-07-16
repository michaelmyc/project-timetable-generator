"""Session state for UI — holds all in-memory session data (ADR-0006)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from timetable_generator.generator.retry import GenerationResult
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan


@dataclass
class SessionState:
    """In-memory session state. All data lost on close (ADR-0006 D1)."""

    global_span: GlobalSpan | None = None
    staff: list[StaffInfo] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    generation_result: GenerationResult | None = None
    holiday_fallback: bool = False

    def set_span(self, start: date, end: date) -> None:
        self.global_span = GlobalSpan(start_date=start, end_date=end)

    def add_staff(
        self,
        name: str,
        job_type: str = "研发人员",
        business_line: str | None = None,
        annual_leave_days: int = 0,
    ) -> None:
        self.staff.append(
            StaffInfo(
                name=name,
                job_type=job_type,
                business_line=business_line,
                annual_leave_days=annual_leave_days,
            )
        )

    def add_project(self, project: Project) -> None:
        self.projects.append(project)

    def clear_result(self) -> None:
        self.generation_result = None

    @property
    def can_generate(self) -> bool:
        """Check if enough data to generate."""
        return self.global_span is not None and len(self.staff) > 0 and len(self.projects) > 0

    @property
    def has_result(self) -> bool:
        return self.generation_result is not None

    def get_staff_ids(self) -> list[str]:
        """Get staff IDs (name-based for MVP)."""
        return [s.name for s in self.staff]
