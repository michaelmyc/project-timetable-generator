"""End-to-end: generate_single → export_csv."""

import csv
from datetime import date
from pathlib import Path

from timetable_generator.export.csv import export_csv
from timetable_generator.generator.greedy import generate_single
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_generate_then_export(tmp_path: Path):
    """Generate records with generate_single, export to CSV, row count = records + 1 header."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    staff = [StaffState.from_changes("u1", [], span)]
    project = Project(
        id="p1",
        name="A",
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 13),
        target_ratio=1.0,
        required_job_types=["研发人员"],
        associated_person_ids=["u1"],
    )
    records = generate_single(
        projects=[project], staff_states=staff, holidays=set(), global_span=span
    )
    assert len(records) > 0

    out = tmp_path / "gen.csv"
    export_csv(records, out)

    with out.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["项目", "员工", "日期", "工时"]
    assert len(rows) == len(records) + 1
    # every data row has 4 columns with YYYY-MM-DD date and integer hours
    for row in rows[1:]:
        assert len(row) == 4
        assert row[2] == date.fromisoformat(row[2]).isoformat()
        assert row[3].isdigit()
