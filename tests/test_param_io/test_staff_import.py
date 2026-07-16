"""Tests for staff CSV import — FR-017 staff param ingestion."""

from pathlib import Path

from timetable_generator.io.staff_csv import import_staff_csv
from timetable_generator.models.staff_info import DEFAULT_JOB_TYPE


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8-sig")
    return path


def test_import_staff_csv(tmp_path: Path):
    """Two data rows → two StaffInfo with parsed fields."""
    csv_text = "姓名,工种,业务线,年假额度\n张三,研发人员,平台,5\n李四,测试,核心,10\n"
    path = _write(tmp_path / "staff.csv", csv_text)
    staff = import_staff_csv(path)
    assert len(staff) == 2
    assert staff[0].name == "张三"
    assert staff[0].job_type == "研发人员"
    assert staff[0].business_line == "平台"
    assert staff[0].annual_leave_days == 5
    assert staff[1].name == "李四"
    assert staff[1].job_type == "测试"
    assert staff[1].business_line == "核心"
    assert staff[1].annual_leave_days == 10


def test_default_job_type(tmp_path: Path):
    """Empty job-type column falls back to DEFAULT_JOB_TYPE ('研发人员')."""
    csv_text = "姓名,工种,业务线,年假额度\n王五,,,0\n"
    path = _write(tmp_path / "default.csv", csv_text)
    staff = import_staff_csv(path)
    assert len(staff) == 1
    assert staff[0].name == "王五"
    assert staff[0].job_type == DEFAULT_JOB_TYPE
    assert staff[0].business_line is None
    assert staff[0].annual_leave_days == 0


def test_default_annual_leave(tmp_path: Path):
    """Missing/empty annual-leave column → 0."""
    csv_text = "姓名,工种,业务线,年假额度\n赵六,研发人员,平台,\n"
    path = _write(tmp_path / "leave.csv", csv_text)
    staff = import_staff_csv(path)
    assert staff[0].annual_leave_days == 0


def test_import_staff_csv_skips_blank_rows(tmp_path: Path):
    """Blank lines are ignored."""
    csv_text = "姓名,工种,业务线,年假额度\n张三,研发人员,平台,3\n\n\n"
    path = _write(tmp_path / "blanks.csv", csv_text)
    staff = import_staff_csv(path)
    assert len(staff) == 1
    assert staff[0].name == "张三"
