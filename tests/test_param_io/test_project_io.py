"""Tests for project CSV/Excel import & export — FR-017 project param ingestion."""

from datetime import date
from pathlib import Path

import pytest

from timetable_generator.io.project_csv import (
    PENDING_PERSON_ID,
    export_projects_csv,
    import_projects_csv,
)
from timetable_generator.models.project import Project


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8-sig")
    return path


DEFAULT_START = date(2026, 1, 1)
DEFAULT_END = date(2026, 3, 31)


def test_import_projects_csv_six_columns(tmp_path: Path):
    csv_text = (
        "项目标识,项目名称,业务线,投入百分比,项目开始时间,项目结束时间\n"
        "p1,项目A,平台,0.3,2026-01-15,2026-02-15\n"
        "p2,项目B,,0.5,,\n"
    )
    path = _write(tmp_path / "projects.csv", csv_text)
    projects = import_projects_csv(path, DEFAULT_START, DEFAULT_END)
    assert len(projects) == 2
    assert projects[0].id == "p1"
    assert projects[0].name == "项目A"
    assert projects[0].business_line == "平台"
    assert projects[0].target_ratio == 0.3
    assert projects[0].start_date == date(2026, 1, 15)
    assert projects[0].end_date == date(2026, 2, 15)
    assert projects[0].required_job_types == []
    assert projects[0].associated_person_ids == [PENDING_PERSON_ID]

    # blank dates fall back to defaults
    assert projects[1].start_date == DEFAULT_START
    assert projects[1].end_date == DEFAULT_END
    assert projects[1].business_line is None


def test_import_projects_csv_missing_columns_raises(tmp_path: Path):
    csv_text = "项目标识,项目名称\np1,A\n"
    path = _write(tmp_path / "bad.csv", csv_text)
    with pytest.raises(ValueError, match="missing required columns"):
        import_projects_csv(path, DEFAULT_START, DEFAULT_END)


def test_import_projects_csv_skips_blank_rows(tmp_path: Path):
    csv_text = (
        "项目标识,项目名称,业务线,投入百分比,项目开始时间,项目结束时间\n"
        "p1,A,平台,0.3,2026-01-01,2026-03-31\n"
        "\n"
        "\n"
    )
    path = _write(tmp_path / "blanks.csv", csv_text)
    projects = import_projects_csv(path, DEFAULT_START, DEFAULT_END)
    assert len(projects) == 1
    assert projects[0].id == "p1"


def test_export_projects_csv_header_and_rows(tmp_path: Path):
    projects = [
        Project(
            id="p1",
            name="项目A",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
            target_ratio=0.3,
            required_job_types=[],
            associated_person_ids=[PENDING_PERSON_ID],
            business_line="平台",
        )
    ]
    path = tmp_path / "out.csv"
    export_projects_csv(projects, path)
    text = path.read_text(encoding="utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0] == "项目标识,项目名称,业务线,投入百分比,项目开始时间,项目结束时间"
    assert lines[1] == "p1,项目A,平台,0.3,2026-01-15,2026-02-15"


def test_export_import_projects_csv_roundtrip(tmp_path: Path):
    """export → import round-trips 6 columns (defaults applied to pending ids)."""
    original = [
        Project(
            id="p1",
            name="项目A",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
            target_ratio=0.3,
            required_job_types=[],
            associated_person_ids=[PENDING_PERSON_ID],
            business_line="平台",
        ),
        Project(
            id="p2",
            name="项目B",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            target_ratio=0.5,
            required_job_types=[],
            associated_person_ids=[PENDING_PERSON_ID],
            business_line=None,
        ),
    ]
    path = tmp_path / "roundtrip.csv"
    export_projects_csv(original, path)
    restored = import_projects_csv(path, DEFAULT_START, DEFAULT_END)
    assert restored == original


def test_projects_xlsx_roundtrip(tmp_path: Path):
    """Excel .xlsx export → import round-trips."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        pytest.skip("openpyxl not installed")

    original = [
        Project(
            id="p1",
            name="项目A",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
            target_ratio=0.3,
            required_job_types=[],
            associated_person_ids=[PENDING_PERSON_ID],
            business_line="平台",
        ),
    ]
    path = tmp_path / "projects.xlsx"
    export_projects_csv(original, path)
    restored = import_projects_csv(path, DEFAULT_START, DEFAULT_END)
    assert restored == original
