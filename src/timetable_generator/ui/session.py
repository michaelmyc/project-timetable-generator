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
    job_types: list[str] = field(default_factory=lambda: ["研发人员"])

    def set_span(self, start: date, end: date) -> None:
        self.global_span = GlobalSpan(start_date=start, end_date=end)

    def add_staff(self, staff: StaffInfo) -> None:
        self.staff.append(staff)

    def update_staff(self, index: int, staff: StaffInfo) -> None:
        if 0 <= index < len(self.staff):
            self.staff[index] = staff

    def remove_staff(self, index: int) -> None:
        if 0 <= index < len(self.staff):
            self.staff.pop(index)

    def add_project(self, project: Project) -> None:
        self.projects.append(project)

    def update_project(self, index: int, project: Project) -> None:
        if 0 <= index < len(self.projects):
            self.projects[index] = project

    def remove_project(self, index: int) -> None:
        if 0 <= index < len(self.projects):
            self.projects.pop(index)

    def clear_result(self) -> None:
        self.generation_result = None

    @property
    def can_generate(self) -> bool:
        return self.global_span is not None and len(self.staff) > 0 and len(self.projects) > 0

    @property
    def has_result(self) -> bool:
        return self.generation_result is not None

    def get_staff_ids(self) -> list[str]:
        return [s.name for s in self.staff]

    def get_job_types(self) -> list[str]:
        """Return the session-level job type list (not computed from staff)."""
        return self.job_types

    def add_job_type(self, jt: str) -> None:
        """Add a job type to the session list if not already present."""
        jt = jt.strip() if jt else ""
        if jt and jt not in self.job_types:
            self.job_types.append(jt)

    def add_job_types(self, jts: list[str]) -> None:
        """Add multiple job types to the session list."""
        for jt in jts:
            self.add_job_type(jt)

    def get_business_lines(self) -> list[str]:
        """Computed property: unique business lines from all staff + projects."""
        lines: set[str] = set()
        for s in self.staff:
            if s.business_line:
                lines.add(s.business_line)
        for p in self.projects:
            if p.business_line:
                lines.add(p.business_line)
        return list(lines)
