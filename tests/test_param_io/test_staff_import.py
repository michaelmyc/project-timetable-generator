"""Tests for staff CSV/Excel import & export — FR-017 staff param ingestion."""

from datetime import date
from pathlib import Path

import pytest

from timetable_generator.io.staff_csv import export_staff_csv, import_staff_csv
from timetable_generator.models.staff_info import DEFAULT_JOB_TYPE, StaffInfo


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8-sig")
    return path


def test_import_staff_csv_five_columns(tmp_path: Path):
    """5-column CSV parses onboard/leave dates."""
    csv_text = (
        "员工,工种,业务线,入职时间,离职时间\n"
        "张三,研发人员,平台,2025-01-01,2026-12-31\n"
        "李四,测试,核心,,\n"
    )
    path = _write(tmp_path / "staff.csv", csv_text)
    staff = import_staff_csv(path)
    assert len(staff) == 2
    assert staff[0].name == "张三"
    assert staff[0].job_type == "研发人员"
    assert staff[0].business_line == "平台"
    assert staff[0].onboard_date == date(2025, 1, 1)
    assert staff[0].leave_date == date(2026, 12, 31)
    assert staff[1].name == "李四"
    assert staff[1].onboard_date is None
    assert staff[1].leave_date is None


def test_default_job_type(tmp_path: Path):
    """Empty job-type column falls back to DEFAULT_JOB_TYPE ('研发人员')."""
    csv_text = "员工,工种,业务线,入职时间,离职时间\n王五,,,,\n"
    path = _write(tmp_path / "default.csv", csv_text)
    staff = import_staff_csv(path)
    assert len(staff) == 1
    assert staff[0].name == "王五"
    assert staff[0].job_type == DEFAULT_JOB_TYPE
    assert staff[0].business_line is None
    assert staff[0].onboard_date is None
    assert staff[0].leave_date is None


def test_import_staff_csv_skips_blank_rows(tmp_path: Path):
    """Blank lines are ignored."""
    csv_text = "员工,工种,业务线,入职时间,离职时间\n张三,研发人员,平台,2025-01-01,\n\n\n"
    path = _write(tmp_path / "blanks.csv", csv_text)
    staff = import_staff_csv(path)
    assert len(staff) == 1
    assert staff[0].name == "张三"


def test_import_staff_csv_missing_columns_raises(tmp_path: Path):
    csv_text = "员工,工种\n张三,研发人员\n"
    path = _write(tmp_path / "bad.csv", csv_text)
    with pytest.raises(ValueError, match="missing required columns"):
        import_staff_csv(path)


def test_export_staff_csv_roundtrip(tmp_path: Path):
    """export → import round-trips all 5 columns."""
    original = [
        StaffInfo(
            name="张三",
            job_type="研发人员",
            business_line="平台",
            onboard_date=date(2025, 1, 1),
            leave_date=date(2026, 12, 31),
        ),
        StaffInfo(name="李四", job_type="测试"),
    ]
    path = tmp_path / "out.csv"
    export_staff_csv(original, path)
    restored = import_staff_csv(path)
    assert restored == original


def test_export_staff_csv_header_and_rows(tmp_path: Path):
    staff = [StaffInfo(name="张三", job_type="研发人员", business_line="平台")]
    path = tmp_path / "out.csv"
    export_staff_csv(staff, path)
    text = path.read_text(encoding="utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0] == "员工,工种,业务线,入职时间,离职时间"
    assert lines[1].startswith("张三,研发人员,平台,")


def test_staff_xlsx_roundtrip(tmp_path: Path):
    """Excel .xlsx export → import round-trips."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        pytest.skip("openpyxl not installed")

    original = [
        StaffInfo(
            name="张三",
            job_type="研发人员",
            business_line="平台",
            onboard_date=date(2025, 1, 1),
            leave_date=date(2026, 12, 31),
        ),
        StaffInfo(name="李四", job_type="测试"),
    ]
    path = tmp_path / "staff.xlsx"
    export_staff_csv(original, path)
    restored = import_staff_csv(path)
    assert restored == original
