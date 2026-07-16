"""E2E integration test — full M1 pipeline without UI."""

from datetime import date

from timetable_generator.export.csv import export_csv
from timetable_generator.generator.retry import GenerationError, generate_with_retry
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_full_m1_cli_pipeline(tmp_path):
    """Full M1 flow: setup → generate → validate → export CSV.

    2 persons, 2 projects, 3 months span.
    """
    span = GlobalSpan(date(2026, 1, 1), date(2026, 3, 31))
    staff = [
        StaffState.from_changes("张三", [], span),
        StaffState.from_changes("李四", [], span),
    ]
    projects = [
        Project(
            id="p1",
            name="支付系统",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            target_ratio=0.3,
            required_job_types=["研发人员"],
            associated_person_ids=["张三", "李四"],
        ),
        Project(
            id="p2",
            name="风控系统",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            target_ratio=0.2,
            required_job_types=["研发人员"],
            associated_person_ids=["张三", "李四"],
        ),
    ]

    # Generate
    result = generate_with_retry(
        projects=projects,
        staff_states=staff,
        holidays=set(),
        global_span=span,
        max_retries=10,
    )

    # Validate
    assert result.validation.is_valid, f"Validation failed: {result.validation.violations}"

    # Export CSV
    csv_path = tmp_path / "m1_e2e.csv"
    export_csv(result.records, csv_path)
    assert csv_path.exists()

    # Verify CSV content
    content = csv_path.read_text(encoding="utf-8-sig")
    lines = content.strip().split("\n")
    assert lines[0] == "项目,员工,日期,工时"
    assert len(lines) == len(result.records) + 1  # header + records

    # Verify each project has records
    p1_records = [r for r in result.records if r.project_id == "p1"]
    p2_records = [r for r in result.records if r.project_id == "p2"]
    assert len(p1_records) > 0
    assert len(p2_records) > 0

    # Verify ratio achievement
    p1_hours = sum(r.hours for r in p1_records)
    p2_hours = sum(r.hours for r in p2_records)
    total_capacity = 2 * 63 * 8  # ~63 workdays × 2 persons × 8h (approximate)
    actual_p1_ratio = p1_hours / total_capacity if total_capacity > 0 else 0
    actual_p2_ratio = p2_hours / total_capacity if total_capacity > 0 else 0
    assert abs(actual_p1_ratio - 0.3) < 0.05, f"p1 ratio {actual_p1_ratio:.2%} != 30%"
    assert abs(actual_p2_ratio - 0.2) < 0.05, f"p2 ratio {actual_p2_ratio:.2%} != 20%"


def test_full_m1_param_roundtrip(tmp_path):
    """Param export → import → generate → export CSV. Verify roundtrip."""
    from timetable_generator.io.params import SessionParams, export_params, import_params

    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    projects = [
        Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["张三"]),
    ]

    from timetable_generator.models.staff_info import StaffInfo

    staff = [StaffInfo(name="张三", job_type="研发人员")]

    # Export params
    params = SessionParams(global_span=span, projects=projects, staff=staff)
    params_path = tmp_path / "params.json"
    export_params(params, params_path)
    assert params_path.exists()

    # Import params
    loaded = import_params(params_path)
    assert loaded.global_span.start_date == span.start_date
    assert loaded.global_span.end_date == span.end_date
    assert len(loaded.projects) == 1
    assert loaded.projects[0].id == "p1"
    assert len(loaded.staff) == 1
    assert loaded.staff[0].name == "张三"

    # Generate from loaded params
    staff_states = [StaffState.from_changes(s.name, [], loaded.global_span) for s in loaded.staff]
    result = generate_with_retry(
        projects=loaded.projects,
        staff_states=staff_states,
        holidays=set(),
        global_span=loaded.global_span,
        max_retries=10,
    )
    assert result.validation.is_valid

    # Export CSV
    csv_path = tmp_path / "roundtrip.csv"
    export_csv(result.records, csv_path)
    assert csv_path.exists()
    assert sum(r.hours for r in result.records) > 0


def test_full_m1_conflict_scenario():
    """Two projects with combined ratio > 1.0 → GenerationError."""
    import pytest

    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 6))
    staff = [StaffState.from_changes("u1", [], span)]
    projects = [
        Project("p1", "A", date(2026, 3, 2), date(2026, 3, 6), 0.7, ["研发人员"], ["u1"]),
        Project("p2", "B", date(2026, 3, 2), date(2026, 3, 6), 0.7, ["研发人员"], ["u1"]),
    ]
    with pytest.raises(GenerationError):
        generate_with_retry(
            projects=projects,
            staff_states=staff,
            holidays=set(),
            global_span=span,
            max_retries=5,
        )
