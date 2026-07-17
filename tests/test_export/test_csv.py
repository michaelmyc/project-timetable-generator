"""Tests for CSV export — FR-008: 项目,员工,日期,工时."""

import csv
from datetime import date
from pathlib import Path

from timetable_generator.export.csv import export_csv
from timetable_generator.models.work_hour import WorkHourRecord


def _read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.reader(f)]


def test_csv_export_basic(tmp_path: Path):
    """3 records → header + 3 data rows; columns are 项目,员工,日期,工时."""
    records = [
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 3, 2), hours=8),
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 3, 3), hours=4),
        WorkHourRecord(project_id="p2", person_id="u2", date=date(2026, 3, 4), hours=6),
    ]
    out = tmp_path / "out.csv"
    export_csv(records, out)
    rows = _read_csv(out)
    assert rows[0] == ["项目", "员工", "日期", "工时"]
    assert len(rows) == 4  # header + 3
    assert rows[1] == ["p1", "u1", "2026-03-02", "8"]
    assert rows[2] == ["p1", "u1", "2026-03-03", "4"]
    assert rows[3] == ["p2", "u2", "2026-03-04", "6"]


def test_csv_date_format(tmp_path: Path):
    """Dates must be YYYY-MM-DD."""
    records = [
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 12, 31), hours=8),
    ]
    out = tmp_path / "dates.csv"
    export_csv(records, out)
    rows = _read_csv(out)
    assert rows[1][2] == "2026-12-31"


def test_csv_hours_integer(tmp_path: Path):
    """Hours must serialize as an integer (no decimal)."""
    records = [
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 1, 1), hours=7),
    ]
    out = tmp_path / "hours.csv"
    export_csv(records, out)
    rows = _read_csv(out)
    assert rows[1][3] == "7"  # not "7.0"
    assert "." not in rows[1][3]


def test_csv_empty_records(tmp_path: Path):
    """Empty record list → only header row."""
    out = tmp_path / "empty.csv"
    export_csv([], out)
    rows = _read_csv(out)
    assert rows == [["项目", "员工", "日期", "工时"]]
