"""Staff CSV import — FR-017 staff parameter ingestion.

CSV format (UTF-8, optional BOM):
    姓名,工种,业务线,年假额度
Defaults: empty 工种 → "研发人员"; empty 业务线 → None; empty 年假额度 → 0.
"""

from __future__ import annotations

import csv
from pathlib import Path

from timetable_generator.models.staff_info import DEFAULT_JOB_TYPE, StaffInfo

REQUIRED_COLUMNS = ["姓名", "工种", "业务线", "年假额度"]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def import_staff_csv(path: Path) -> list[StaffInfo]:
    """Import staff profiles from a CSV file at *path*.

    The first row must be a header containing the columns
    姓名, 工种, 业务线, 年假额度 (in any order). Blank data rows are skipped.
    """
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"staff CSV missing required columns: {missing}")

        staff: list[StaffInfo] = []
        for row in reader:
            name = _clean(row.get("姓名"))
            if not name:
                continue  # skip blank rows
            job_type = _clean(row.get("工种")) or DEFAULT_JOB_TYPE
            business_line = _clean(row.get("业务线"))
            leave_raw = _clean(row.get("年假额度"))
            annual_leave_days = int(leave_raw) if leave_raw else 0
            staff.append(
                StaffInfo(
                    name=name,
                    job_type=job_type,
                    business_line=business_line,
                    annual_leave_days=annual_leave_days,
                )
            )
        return staff
