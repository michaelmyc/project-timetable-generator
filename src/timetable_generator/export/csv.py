"""CSV export module — FR-008: 项目,员工,日期,工时 (YYYY-MM-DD, integer hours)."""

from __future__ import annotations

import csv
from pathlib import Path

from timetable_generator.models.work_hour import WorkHourRecord

HEADER = ["项目", "员工", "日期", "工时"]


def export_csv(records: list[WorkHourRecord], path: Path) -> None:
    """Write work-hour records to a CSV file at *path*.

    Columns: 项目, 员工, 日期(YYYY-MM-DD), 工时(integer).
    Uses UTF-8 with BOM so Chinese headers open correctly in Excel.
    """
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for r in records:
            writer.writerow([r.project_id, r.person_id, r.date.isoformat(), r.hours])
