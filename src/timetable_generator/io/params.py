"""SessionParams — JSON serialization for project + staff params (FR-017, ADR-0012).

Enables parameter reuse: export a session's inputs to JSON and re-import them
later to regenerate or share configurations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan


@dataclass
class SessionParams:
    """All inputs needed to (re)run a generation session.

    Attributes:
        global_span: The global generation time range.
        projects: Project definitions for the session.
        staff: Staff profiles (StaffInfo) for the session.
    """

    global_span: GlobalSpan
    projects: list[Project] = field(default_factory=list)
    staff: list[StaffInfo] = field(default_factory=list)


def _serialize_date(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None


def _parse_date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _global_span_to_dict(span: GlobalSpan) -> dict:
    return {
        "start_date": _serialize_date(span.start_date),
        "end_date": _serialize_date(span.end_date),
    }


def _global_span_from_dict(data: dict) -> GlobalSpan:
    return GlobalSpan(
        start_date=date.fromisoformat(data["start_date"]),
        end_date=date.fromisoformat(data["end_date"]),
    )


def _project_to_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "start_date": _serialize_date(p.start_date),
        "end_date": _serialize_date(p.end_date),
        "target_ratio": p.target_ratio,
        "required_job_types": list(p.required_job_types),
        "associated_person_ids": list(p.associated_person_ids),
        "ramp_up_point": _serialize_date(p.ramp_up_point),
        "maintenance_point": _serialize_date(p.maintenance_point),
    }


def _project_from_dict(data: dict) -> Project:
    return Project(
        id=data["id"],
        name=data["name"],
        start_date=date.fromisoformat(data["start_date"]),
        end_date=date.fromisoformat(data["end_date"]),
        target_ratio=data["target_ratio"],
        required_job_types=list(data["required_job_types"]),
        associated_person_ids=list(data["associated_person_ids"]),
        ramp_up_point=_parse_date(data.get("ramp_up_point")),
        maintenance_point=_parse_date(data.get("maintenance_point")),
    )


def _staff_to_dict(s: StaffInfo) -> dict:
    return {
        "name": s.name,
        "job_type": s.job_type,
        "business_line": s.business_line,
        "annual_leave_days": s.annual_leave_days,
    }


def _staff_from_dict(data: dict) -> StaffInfo:
    return StaffInfo(
        name=data["name"],
        job_type=data.get("job_type") or StaffInfo().job_type,
        business_line=data.get("business_line"),
        annual_leave_days=data.get("annual_leave_days", 0),
    )


def _session_to_dict(session: SessionParams) -> dict:
    return {
        "global_span": _global_span_to_dict(session.global_span),
        "projects": [_project_to_dict(p) for p in session.projects],
        "staff": [_staff_to_dict(s) for s in session.staff],
    }


def _session_from_dict(data: dict) -> SessionParams:
    return SessionParams(
        global_span=_global_span_from_dict(data["global_span"]),
        projects=[_project_from_dict(p) for p in data.get("projects", [])],
        staff=[_staff_from_dict(s) for s in data.get("staff", [])],
    )


def export_params(session: SessionParams, path: Path) -> None:
    """Serialize *session* to a JSON file at *path* (dates as ISO strings)."""
    path.write_text(
        json.dumps(_session_to_dict(session), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def import_params(path: Path) -> SessionParams:
    """Read a JSON file at *path* and reconstruct a SessionParams."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return _session_from_dict(data)
