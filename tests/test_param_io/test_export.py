"""Tests for SessionParams JSON export/import — FR-017, ADR-0012."""

import json
from datetime import date
from pathlib import Path

from timetable_generator.io.params import SessionParams, export_params, import_params
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan


def _sample_session() -> SessionParams:
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 27))
    projects = [
        Project(
            id="p1",
            name="项目A",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 27),
            target_ratio=0.5,
            required_job_types=["研发人员"],
            associated_person_ids=["u1", "u2"],
            ramp_up_point=date(2026, 3, 5),
            maintenance_point=date(2026, 3, 20),
            business_line="平台",
        ),
    ]
    staff = [
        StaffInfo(
            name="u1",
            job_type="研发人员",
            business_line="平台",
            annual_leave_days=5,
            onboard_date=date(2025, 1, 1),
            leave_date=date(2026, 12, 31),
        ),
        StaffInfo(name="u2", job_type="测试", business_line=None, annual_leave_days=0),
    ]
    return SessionParams(global_span=span, projects=projects, staff=staff)


def test_export_session_params(tmp_path: Path):
    """Export to JSON; verify key fields present and dates are ISO strings."""
    session = _sample_session()
    out = tmp_path / "params.json"
    export_params(session, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["global_span"]["start_date"] == "2026-03-02"
    assert data["global_span"]["end_date"] == "2026-03-27"
    assert data["projects"][0]["id"] == "p1"
    assert data["projects"][0]["target_ratio"] == 0.5
    assert data["projects"][0]["ramp_up_point"] == "2026-03-05"
    assert data["projects"][0]["maintenance_point"] == "2026-03-20"
    assert data["staff"][0]["name"] == "u1"
    assert data["staff"][0]["business_line"] == "平台"
    assert data["staff"][0]["onboard_date"] == "2025-01-01"
    assert data["staff"][0]["leave_date"] == "2026-12-31"
    assert data["staff"][1]["business_line"] is None
    assert data["staff"][1]["onboard_date"] is None
    assert data["staff"][1]["leave_date"] is None
    assert data["projects"][0]["business_line"] == "平台"


def test_import_params(tmp_path: Path):
    """export → import yields a SessionParams equal to the original."""
    original = _sample_session()
    out = tmp_path / "roundtrip.json"
    export_params(original, out)

    restored = import_params(out)
    assert restored == original
    assert restored.global_span == original.global_span
    assert restored.projects == original.projects
    assert restored.staff == original.staff


def test_import_params_no_optional_points(tmp_path: Path):
    """Projects without ramp_up/maintenance points round-trip as None."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    projects = [
        Project(
            id="p1",
            name="A",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 6),
            target_ratio=1.0,
            required_job_types=["研发人员"],
            associated_person_ids=["u1"],
        ),
    ]
    staff = [StaffInfo(name="u1")]
    session = SessionParams(global_span=span, projects=projects, staff=staff)
    out = tmp_path / "simple.json"
    export_params(session, out)

    restored = import_params(out)
    assert restored == session
    assert restored.projects[0].ramp_up_point is None
    assert restored.projects[0].maintenance_point is None
