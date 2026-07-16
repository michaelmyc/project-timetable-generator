"""NiceGUI UI — build the full MVP interface.

Single-page workflow: global span → staff list → project batch → generate → export.
All in-memory, no persistence (ADR-0006).
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from nicegui import ui

from timetable_generator.export.csv import export_csv
from timetable_generator.generator.retry import generate_with_retry
from timetable_generator.holiday.cache import HolidayCache
from timetable_generator.holiday.orchestrator import HolidayOrchestrator
from timetable_generator.io.params import SessionParams, export_params
from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import StaffState
from timetable_generator.ui.session import SessionState


def build_ui() -> SessionState:
    """Build the UI and return the session state for testing."""
    session = SessionState()

    ui.label("排班打卡时间表生成器").classes("text-h4 q-mb-md")

    # Step 1: Global Span
    ui.label("1. 全局生成区间").classes("text-h6")
    with ui.row():
        start_input = ui.input(label="开始日期 (YYYY-MM-DD)", value="2026-01-01")
        end_input = ui.input(label="结束日期 (YYYY-MM-DD)", value="2026-06-30")
        ui.button("设定区间", on_click=lambda: _set_span(session, start_input, end_input))
    span_label = ui.label("区间未设定")

    # Step 2: Staff
    ui.label("2. 员工名单").classes("text-h6 q-mt-md")
    with ui.row():
        staff_name_input = ui.input(label="员工姓名")
        staff_job_input = ui.input(label="工种（默认研发人员）", value="研发人员")
        ui.button(
            "添加员工", on_click=lambda: _add_staff(session, staff_name_input, staff_job_input)
        )
    staff_table = ui.table(
        columns=[
            {"name": "name", "label": "姓名", "field": "name"},
            {"name": "job_type", "label": "工种", "field": "job_type"},
        ],
        rows=[],
        row_key="name",
    )

    # Step 3: Projects
    ui.label("3. 项目批次").classes("text-h6 q-mt-md")
    with ui.row():
        proj_id_input = ui.input(label="项目标识")
        proj_name_input = ui.input(label="项目名称")
        proj_ratio_input = ui.number(label="投入比例 (0-1)", value=0.3, min=0, max=1, step=0.01)
    proj_jobs_input = ui.input(label="所需工种（逗号分隔）", value="研发人员")
    ui.button(
        "添加项目",
        on_click=lambda: _add_project(
            session, proj_id_input, proj_name_input, proj_ratio_input, proj_jobs_input, span_label
        ),
    )
    project_list = ui.column()

    # Step 4: Generate
    ui.label("4. 生成").classes("text-h6 q-mt-md")
    ui.button("生成工时表", on_click=lambda: _generate(session, progress_label, result_label))
    progress_label = ui.label("")
    result_label = ui.label("")

    # Step 5: Export
    ui.label("5. 导出").classes("text-h6 q-mt-md")
    ui.button("导出 CSV", on_click=lambda: _export_csv(session))
    ui.button("导出配置", on_click=lambda: _export_params(session))

    # Store refs for testing
    session._span_label = span_label  # type: ignore[attr-defined]
    session._staff_table = staff_table  # type: ignore[attr-defined]
    session._project_list = project_list  # type: ignore[attr-defined]

    return session


def _set_span(session: SessionState, start_input, end_input) -> None:
    start = date.fromisoformat(str(start_input.value).strip())
    end = date.fromisoformat(str(end_input.value).strip())
    session.set_span(start, end)
    session._span_label.text = f"区间: {start} → {end}"  # type: ignore[attr-defined]


def _add_staff(session: SessionState, name_input, job_input) -> None:
    name = name_input.value.strip()
    if not name:
        return
    job = job_input.value.strip() or "研发人员"
    session.add_staff(name=name, job_type=job)
    name_input.value = ""
    rows = [{"name": s.name, "job_type": s.job_type, "id": s.name} for s in session.staff]
    session._staff_table.update_rows(rows)  # type: ignore[attr-defined]


def _add_project(
    session: SessionState, id_input, name_input, ratio_input, jobs_input, span_label
) -> None:
    if session.global_span is None:
        ui.notify("请先设定全局区间", type="warning")
        return
    pid = id_input.value.strip()
    pname = name_input.value.strip()
    if not pid or not pname:
        ui.notify("项目标识和名称不能为空", type="warning")
        return
    ratio = float(ratio_input.value)
    jobs = [j.strip() for j in jobs_input.value.split(",") if j.strip()]
    staff_ids = session.get_staff_ids()
    if not staff_ids:
        ui.notify("请先添加员工", type="warning")
        return
    project = Project(
        id=pid,
        name=pname,
        start_date=session.global_span.start_date,
        end_date=session.global_span.end_date,
        target_ratio=ratio,
        required_job_types=jobs,
        associated_person_ids=staff_ids,
    )
    session.add_project(project)
    id_input.value = ""
    name_input.value = ""
    ui.notify(f"项目 {pname} 已添加")
    session._project_list.clear()  # type: ignore[attr-defined]
    with session._project_list:  # type: ignore[attr-defined]
        for p in session.projects:
            ui.label(
                f"  {p.id} | {p.name} | 比例 {p.target_ratio:.0%} | 工种 {', '.join(p.required_job_types)}"
            )


def _generate(session: SessionState, progress_label, result_label) -> None:
    if not session.can_generate:
        ui.notify("请先设定区间、添加员工和项目", type="warning")
        return
    progress_label.text = "正在生成..."
    result_label.text = ""
    try:
        span = session.global_span
        assert span is not None
        staff_states = [StaffState.from_changes(s.name, [], span) for s in session.staff]

        # Holidays
        cache = HolidayCache(_get_cache_dir())
        orch = HolidayOrchestrator(cache=cache)
        years = range(span.start_date.year, span.end_date.year + 1)
        resolver = asyncio.run(orch.ensure_years(*years))
        holidays: set[date] = set()
        session.holiday_fallback = resolver.is_fallback

        result = generate_with_retry(
            projects=session.projects,
            staff_states=staff_states,
            holidays=holidays,
            global_span=span,
            max_retries=10,
        )
        session.generation_result = result
        progress_label.text = f"生成完成（{result.attempts} 次尝试）"
        total_hours = sum(r.hours for r in result.records)
        ratios = ", ".join(
            f"{pid}: {ratio:.1%}" for pid, ratio in result.validation.ratio_achievement.items()
        )
        result_label.text = f"总工时: {total_hours}h | 比例达成: {ratios}"

        if session.holiday_fallback:
            ui.notify(
                "⚠️ 节假日数据获取失败，已降级为仅周末排除，结果可能不符合法定节假日",
                type="warning",
            )
    except Exception as e:
        progress_label.text = f"生成失败: {e}"
        ui.notify(f"生成失败: {e}", type="negative")


def _export_csv(session: SessionState) -> None:
    if not session.has_result:
        ui.notify("请先生成", type="warning")
        return
    path = Path("output.csv")
    export_csv(session.generation_result.records, path)
    ui.notify(f"CSV 已导出: {path.resolve()}")


def _export_params(session: SessionState) -> None:
    if session.global_span is None:
        ui.notify("请先设定区间", type="warning")
        return
    params = SessionParams(
        global_span=session.global_span,
        projects=session.projects,
        staff=session.staff,
    )
    path = Path("params.json")
    export_params(params, path)
    ui.notify(f"配置已导出: {path.resolve()}")


def _get_cache_dir() -> Path:
    """Get holiday cache directory (platform-specific, ADR-0013 D3)."""
    import os
    import sys

    app_name = "timetable-generator"
    if sys.platform == "darwin":
        base = Path(os.path.expanduser("~/Library/Caches"))
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")))
    return base / app_name / "holidays"
