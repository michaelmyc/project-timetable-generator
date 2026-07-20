"""NiceGUI UI — build the full MVP interface (overhauled).

Features:
- Sticky top navigation with 5 tabs: 区间设置 / 员工管理 / 项目管理 / 校验与生成 / 结果导出
- Staff management: add/edit/delete + CSV/Excel import/export (sticky bottom action bar)
- Project management: add/edit/delete + CSV/Excel import/export (sticky bottom action bar)
- 校验并生成 combined button (validates first, then generates)
- Algorithm explanation panel placed before the generate button
- Wider dialogs with full-width form inputs
- Project target ratio input as percentage (0-100), stored as 0.0-1.0
- CSV-only export (JSON config export removed)
- All unused fields preserved in import/export but not editable in MVP
"""

from __future__ import annotations

import asyncio
import sys
import threading
from datetime import date
from pathlib import Path

from nicegui import ui

from timetable_generator.export.csv import export_csv
from timetable_generator.generator.retry import generate_with_retry
from timetable_generator.holiday.cache import HolidayCache
from timetable_generator.holiday.orchestrator import HolidayOrchestrator
from timetable_generator.io.project_csv import export_projects_csv, import_projects_csv
from timetable_generator.io.staff_csv import export_staff_csv, import_staff_csv
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import DEFAULT_JOB_TYPE, StaffInfo
from timetable_generator.models.staff_state import StaffState
from timetable_generator.ui.session import SessionState

RATIO_TOLERANCE = 0.08


async def _download_file(data: bytes, filename: str) -> None:
    """Download file: native mode uses pywebview save dialog, web mode uses ui.download."""

    if "--native" in sys.argv or getattr(sys, "frozen", False):
        # Native/webview mode: use NiceGUI main_window save dialog
        from nicegui import app as nicegui_app
        from webview import FileDialog

        window = nicegui_app.native.main_window
        if window is not None:
            result = await window.create_file_dialog(
                FileDialog.SAVE,
                save_filename=filename,
                file_types=("CSV files (*.csv)", "JSON files (*.json)", "All files (*.*)"),
            )
            if result:
                save_path = result if isinstance(result, str) else result[0]
                Path(save_path).write_bytes(data)
                ui.notify(f"已保存: {save_path}", type="positive")
            else:
                ui.notify("已取消保存", type="warning")
        else:
            # Fallback: write to cwd
            Path(filename).write_bytes(data)
            ui.notify(f"已保存: {Path(filename).resolve()}", type="positive")
    else:
        # Web server mode: trigger browser download
        ui.download(data, filename=filename)


def build_ui() -> SessionState:
    """Build the UI and return the session state for testing."""
    session = SessionState()

    ui.label("排班打卡时间表生成器").classes("text-h4 q-mb-md")

    # Inject CSS before rendering (ensure sticky works)
    ui.add_head_html("""<style>
    .sticky-top { position: sticky !important; top: 0; z-index: 1000; background: white; }
    .sticky-bottom-bar { position: fixed; bottom: 0; left: 0; right: 0; background: white; padding: 10px; z-index: 1000; border-top: 1px solid #eee; }
    </style>""")

    # --- Sticky top navigation with tabs ---
    with ui.row().classes("sticky-top w-full no-wrap") as _header, ui.tabs() as tabs:
        ui.tab("区间设置")
        ui.tab("员工管理")
        ui.tab("项目管理")
        ui.tab("校验与生成")
        ui.tab("结果导出")

    # --- Tab panels ---
    panels = ui.tab_panels(tabs, value="区间设置").classes("w-full").style("margin-top: 50px")
    with panels:
        with ui.tab_panel("区间设置"):
            _build_global_span(session)
        with ui.tab_panel("员工管理"):
            _build_staff_management(session)
        with ui.tab_panel("项目管理"):
            _build_project_management(session)
        with ui.tab_panel("校验与生成"):
            _build_validate_and_generate(session)
        with ui.tab_panel("结果导出"):
            _build_export(session)

    # --- Global fixed bottom action bar (outside tab panels) ---
    staff_bottom = (
        ui.row()
        .classes("sticky-bottom-bar w-full")
        .bind_visibility_from(panels, "value", backward=lambda v: v == "员工管理")
    )
    with staff_bottom:
        ui.button(
            "添加员工", on_click=lambda: _show_staff_dialog(session, session._staff_table, None)
        )  # type: ignore[attr-defined]
        ui.button(
            "删除选中", on_click=lambda: _delete_selected_staff(session, session._staff_table)
        )  # type: ignore[attr-defined]

    project_bottom = (
        ui.row()
        .classes("sticky-bottom-bar w-full")
        .bind_visibility_from(panels, "value", backward=lambda v: v == "项目管理")
    )
    with project_bottom:
        ui.button(
            "添加项目", on_click=lambda: _show_project_dialog(session, session._project_table, None)
        )  # type: ignore[attr-defined]
        ui.button(
            "删除选中", on_click=lambda: _delete_selected_project(session, session._project_table)
        )  # type: ignore[attr-defined]


# --- Tab 1: Global Span (calendar) ---
def _build_global_span(session: SessionState) -> None:
    ui.label("全局生成区间").classes("text-subtitle1")

    def _on_change(_e=None) -> None:
        start_val = start_picker.value
        end_val = end_picker.value
        if not start_val or not end_val:
            return
        try:
            start = date.fromisoformat(str(start_val))
            end = date.fromisoformat(str(end_val))
        except ValueError:
            ui.notify("日期格式不合法", type="warning")
            return
        if end < start:
            ui.notify("结束日期不能早于开始日期", type="warning")
            return
        session.set_span(start, end)

    with ui.row():
        start_picker = ui.date_input(label="开始日期", on_change=_on_change).classes("w-full")
        end_picker = ui.date_input(label="结束日期", on_change=_on_change).classes("w-full")


# --- Tab 2: Staff Management ---
def _build_staff_management(session: SessionState) -> None:
    ui.label("员工管理").classes("text-h6")

    # Import/Export buttons
    with ui.row():
        ui.button("导入员工", on_click=lambda: _import_staff(session, staff_table))
        ui.button("导出员工", on_click=lambda: _export_staff(session))

    # Staff table
    staff_table = ui.table(
        columns=[
            {"name": "name", "label": "员工", "field": "name"},
            {"name": "job_type", "label": "工种", "field": "job_type"},
            {"name": "business_line", "label": "业务线【暂不考虑】", "field": "business_line"},
            {"name": "onboard_date", "label": "入职时间", "field": "onboard_date"},
            {"name": "leave_date", "label": "离职时间", "field": "leave_date"},
            {"name": "actions", "label": "操作", "field": "actions"},
        ],
        rows=[],
        row_key="name",
        selection="multiple",
    ).style("margin-bottom: 80px")
    staff_table.add_slot(
        "body-cell-actions",
        r"""
        <q-td :props="props">
            <q-btn flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
        </q-td>
        """,
    )
    staff_table.on("edit", lambda e: _on_edit_staff(session, staff_table, e.args))

    session._staff_table = staff_table  # type: ignore[attr-defined]


def _show_staff_dialog(session, staff_table, edit_index: int | None) -> None:
    """Show add/edit staff dialog. edit_index=None for add, index for edit."""
    with ui.dialog() as dialog, ui.card().style("width: 800px; max-width: 90vw"):
        title = "编辑员工" if edit_index is not None else "添加员工"
        ui.label(title).classes("text-h6")

        existing = session.staff[edit_index] if edit_index is not None else None

        name_input = ui.input(label="员工姓名", value=existing.name if existing else "").classes(
            "w-full"
        )
        job_input = ui.select(
            label="工种",
            options=session.job_types,
            value=existing.job_type if existing else DEFAULT_JOB_TYPE,
            with_input=True,
            new_value_mode="add",
        ).classes("w-full")
        bl_input = ui.select(
            label="业务线【暂不考虑】",
            options=session.business_lines,
            value=existing.business_line if existing else None,
            with_input=True,
            new_value_mode="add",
        ).classes("w-full")
        # Onboard/leave dates: affect active span and capacity
        onboard_input = ui.date_input(
            label="入职时间",
            value=existing.onboard_date.isoformat() if existing and existing.onboard_date else None,
        ).classes("w-full")
        leave_input = ui.date_input(
            label="离职时间",
            value=existing.leave_date.isoformat() if existing and existing.leave_date else None,
        ).classes("w-full")

        def _save():
            name = (name_input.value or "").strip()
            if not name:
                ui.notify("姓名不能为空", type="warning")
                return
            job = str(job_input.value or "").strip() or DEFAULT_JOB_TYPE
            session.add_job_type(job)
            bl = str(bl_input.value or "").strip() or None
            if bl:
                session.add_business_line(bl)
            onboard = date.fromisoformat(str(onboard_input.value)) if onboard_input.value else None
            leave = date.fromisoformat(str(leave_input.value)) if leave_input.value else None
            staff = StaffInfo(
                name=name,
                job_type=job,
                business_line=bl,
                onboard_date=onboard,
                leave_date=leave,
            )
            if edit_index is not None:
                session.update_staff(edit_index, staff)
            else:
                session.add_staff(staff)
            _refresh_staff_table(session, staff_table)
            dialog.close()

        with ui.row():
            ui.button("保存", on_click=_save)
            ui.button("取消", on_click=dialog.close)

    dialog.open()


def _on_edit_staff(session, staff_table, row) -> None:
    name = row.get("name", "") if isinstance(row, dict) else ""
    index = next((i for i, s in enumerate(session.staff) if s.name == name), None)
    if index is not None:
        _show_staff_dialog(session, staff_table, index)


def _delete_selected_staff(session, staff_table) -> None:
    """Delete all selected staff rows (multi-select)."""
    selected = getattr(staff_table, "selected", []) or []
    if not selected:
        ui.notify("请先选择行", type="warning")
        return
    names_to_delete = {r.get("name", "") for r in selected}
    # Remove in reverse order to keep indices valid
    for i in range(len(session.staff) - 1, -1, -1):
        if session.staff[i].name in names_to_delete:
            session.remove_staff(i)
    _refresh_staff_table(session, staff_table)
    ui.notify(f"已删除 {len(names_to_delete)} 名员工")


def _refresh_staff_table(session, staff_table) -> None:
    rows = []
    for s in session.staff:
        rows.append(
            {
                "name": s.name,
                "job_type": s.job_type,
                "business_line": s.business_line or "—",
                "onboard_date": s.onboard_date.isoformat() if s.onboard_date else "—",
                "leave_date": s.leave_date.isoformat() if s.leave_date else "—",
            }
        )
    staff_table.update_rows(rows)


def _import_staff(session, staff_table) -> None:
    """Import staff via file picker (ui.upload)."""
    with ui.dialog() as dialog, ui.card().style("width: 800px; max-width: 90vw"):
        ui.label("导入员工").classes("text-h6")
        ui.label("格式: 员工,工种,业务线,入职时间,离职时间 (CSV 或 Excel)").classes("text-caption")

        async def _on_upload(e):
            try:
                import tempfile

                tmp = Path(tempfile.mktemp(suffix=Path(e.file.name).suffix))
                await e.file.save(tmp)
                imported = import_staff_csv(tmp)
                session.staff.extend(imported)
                session.add_job_types([s.job_type for s in imported if s.job_type])
                session.add_business_lines([s.business_line for s in imported if s.business_line])
                _refresh_staff_table(session, staff_table)
                ui.notify(f"导入 {len(imported)} 名员工", type="positive")
                dialog.close()
            except Exception as ex:
                ui.notify(f"导入失败: {ex}", type="negative")

        ui.upload(label="选择文件", on_upload=_on_upload, auto_upload=True).classes("w-full").props(
            'accept=".csv,.xlsx,.xlsm"'
        )
        with ui.row():
            ui.button("取消", on_click=dialog.close)
    dialog.open()


async def _export_staff(session) -> None:
    """Export staff to CSV via browser download."""
    if not session.staff:
        ui.notify("没有员工可导出", type="warning")
        return
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".csv"))
    export_staff_csv(session.staff, tmp)
    await _download_file(tmp.read_bytes(), filename="staff_export.csv")


# --- Tab 3: Project Management ---
def _build_project_management(session: SessionState) -> None:
    ui.label("项目管理").classes("text-h6")

    with ui.row():
        ui.button("导入项目", on_click=lambda: _import_projects(session))
        ui.button("导出项目", on_click=lambda: _export_projects(session))
    project_table = ui.table(
        columns=[
            {"name": "name", "label": "项目名称", "field": "name"},
            {"name": "target_ratio", "label": "投入比例", "field": "target_ratio"},
            {"name": "required_job_types", "label": "所需工种", "field": "required_job_types"},
            {"name": "business_line", "label": "业务线【暂不考虑】", "field": "business_line"},
            {"name": "start_date", "label": "开始时间", "field": "start_date"},
            {"name": "end_date", "label": "结束时间", "field": "end_date"},
            {"name": "actions", "label": "操作", "field": "actions"},
        ],
        rows=[],
        row_key="name",
        selection="multiple",
    ).style("margin-bottom: 80px")
    project_table.add_slot(
        "body-cell-actions",
        r"""
        <q-td :props="props">
            <q-btn flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
        </q-td>
        """,
    )
    project_table.on("edit", lambda e: _on_edit_project(session, project_table, e.args))

    session._project_table = project_table  # type: ignore[attr-defined]


def _show_project_dialog(session, project_table, edit_index: int | None) -> None:
    with ui.dialog() as dialog, ui.card().style("width: 800px; max-width: 90vw"):
        title = "编辑项目" if edit_index is not None else "添加项目"
        ui.label(title).classes("text-h6")

        existing = session.projects[edit_index] if edit_index is not None else None
        pname_input = ui.input(label="项目名称", value=existing.name if existing else "").classes(
            "w-full"
        )
        # Business line: select from session list, allow new
        bl_input = ui.select(
            label="业务线",
            options=session.business_lines,
            value=existing.business_line if existing else None,
            with_input=True,
            new_value_mode="add",
        ).classes("w-full")
        ratio_input = ui.number(
            label="投入比例 (%)",
            value=existing.target_ratio * 100 if existing else 30,
            min=0,
            max=100,
            step=1,
        ).classes("w-full")
        start_input = ui.date_input(label="项目开始日期（可空，生成时用全局区间）").classes(
            "w-full"
        )
        end_input = ui.date_input(label="项目结束日期（可空，生成时用全局区间）").classes("w-full")
        if existing:
            start_input.value = existing.start_date.isoformat()
            end_input.value = existing.end_date.isoformat()

        # Job types: select from session list, multiple, allow new
        jobs_input = ui.select(
            label="所需工种（可空=不设约束；可多选或输入新建）",
            options=session.job_types,
            value=existing.required_job_types if existing and existing.required_job_types else [],
            multiple=True,
            with_input=True,
            new_value_mode="add",
        ).classes("w-full")

        def _save():
            pname = (pname_input.value or "").strip()
            if not pname:
                ui.notify("项目名称不能为空", type="warning")
                return
            pid = pname  # id = name (合并)
            ratio = float(ratio_input.value) / 100 if ratio_input.value is not None else 0.0
            bl = str(bl_input.value or "").strip() or None
            if bl:
                session.add_business_line(bl)
            # Dates: use date_input values; if empty, None (resolved at generation time)
            sd = date.fromisoformat(str(start_input.value)) if start_input.value else None
            ed = date.fromisoformat(str(end_input.value)) if end_input.value else None
            selected_jobs = jobs_input.value or []
            if isinstance(selected_jobs, str):
                selected_jobs = [selected_jobs]
            jobs = [str(j).strip() for j in selected_jobs if str(j).strip()]
            session.add_job_types(jobs)
            # associated_person_ids: empty = all staff (resolved at generation time)
            staff_ids = session.get_staff_ids()
            project = Project(
                id=pid,
                name=pname,
                start_date=sd,
                end_date=ed,
                target_ratio=ratio,
                required_job_types=jobs,
                associated_person_ids=staff_ids,
                business_line=bl,
            )
            if edit_index is not None:
                session.update_project(edit_index, project)
            else:
                session.add_project(project)
            _refresh_project_table(session, project_table)
            dialog.close()

        with ui.row():
            ui.button("保存", on_click=_save)
            ui.button("取消", on_click=dialog.close)
    dialog.open()


def _on_edit_project(session, project_table, row) -> None:
    """Edit a project row triggered by the in-row edit button."""
    pname = row.get("name", "") if isinstance(row, dict) else ""
    index = next((i for i, p in enumerate(session.projects) if p.name == pname), None)
    if index is not None:
        _show_project_dialog(session, project_table, index)


def _delete_selected_project(session, project_table) -> None:
    """Delete all selected project rows (multi-select)."""
    selected = getattr(project_table, "selected", []) or []
    if not selected:
        ui.notify("请先选择行", type="warning")
        return
    names_to_delete = {r.get("name", "") for r in selected}
    for i in range(len(session.projects) - 1, -1, -1):
        if session.projects[i].name in names_to_delete:
            session.remove_project(i)
    _refresh_project_table(session, project_table)
    ui.notify(f"已删除 {len(names_to_delete)} 个项目")


def _refresh_project_table(session, project_table) -> None:
    rows = []
    for p in session.projects:
        rows.append(
            {
                "name": p.name,
                "target_ratio": f"{p.target_ratio:.0%}",
                "required_job_types": ", ".join(p.required_job_types)
                if p.required_job_types
                else "无约束",
                "business_line": p.business_line or "—",
                "start_date": p.start_date.isoformat() if p.start_date else "—",
                "end_date": p.end_date.isoformat() if p.end_date else "—",
            }
        )
    project_table.update_rows(rows)


def _import_projects(session) -> None:
    """Import projects via file picker (ui.upload)."""
    with ui.dialog() as dialog, ui.card().style("width: 800px; max-width: 90vw"):
        ui.label("导入项目").classes("text-h6")
        ui.label("格式: 项目名称,业务线,投入百分比,项目开始时间,项目结束时间").classes(
            "text-caption"
        )

        async def _on_upload(e):
            try:
                import tempfile

                tmp = Path(tempfile.mktemp(suffix=Path(e.file.name).suffix))
                await e.file.save(tmp)
                imported = import_projects_csv(tmp)
                session.projects.extend(imported)
                for p in imported:
                    session.add_job_types(p.required_job_types)
                    if p.business_line:
                        session.add_business_line(p.business_line)
                _refresh_project_table(session, session._project_table)  # type: ignore[attr-defined]
                ui.notify(f"导入 {len(imported)} 个项目", type="positive")
                dialog.close()
            except Exception as ex:
                ui.notify(f"导入失败: {ex}", type="negative")

        ui.upload(label="选择文件", on_upload=_on_upload, auto_upload=True).classes("w-full").props(
            'accept=".csv,.xlsx,.xlsm"'
        )
        with ui.row():
            ui.button("取消", on_click=dialog.close)
    dialog.open()


async def _export_projects(session) -> None:
    """Export projects to CSV via browser download."""
    if not session.projects:
        ui.notify("没有项目可导出", type="warning")
        return
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".csv"))
    export_projects_csv(session.projects, tmp)
    await _download_file(tmp.read_bytes(), filename="projects_export.csv")


# --- Tab 4: Validate & Generate ---
def _build_validate_and_generate(session: SessionState) -> None:
    ui.label("校验与生成").classes("text-h6")

    # Validate & generate button FIRST
    ui.button(
        "校验并生成", on_click=lambda: _validate_and_generate(session, progress_label, result_label)
    )
    progress_label = ui.label("")
    result_label = ui.label("")
    session._progress_label = progress_label  # type: ignore[attr-defined]
    session._result_label = result_label  # type: ignore[attr-defined]
    session._validation_label = result_label  # type: ignore[attr-defined]

    # Algorithm info AFTER the generate button
    _build_algorithm_info()


async def _validate_and_generate(session, progress_label, result_label) -> None:
    """Validate first; if passed, generate; otherwise show issues."""
    issues = _collect_validation_issues(session)
    if issues:
        result_label.text = "\n".join(issues)
        ui.notify(f"发现 {len(issues)} 个问题，请先修复", type="warning")
        return
    result_label.text = "✅ 校验通过，开始生成..."
    await _generate(session, progress_label, result_label)


def _collect_validation_issues(session) -> list[str]:
    issues: list[str] = []

    if session.global_span is None:
        issues.append("❌ 全局生成区间未设定")
    if not session.staff:
        issues.append("❌ 没有员工")
    if not session.projects:
        issues.append("❌ 没有项目")

    # Check job type coverage
    staff_job_types = {s.job_type for s in session.staff}
    for p in session.projects:
        missing = set(p.required_job_types) - staff_job_types
        if missing:
            issues.append(f"❌ 项目 {p.name} 缺少工种: {missing}")

    # Check business line consistency (informational, 暂不考虑)
    staff_lines = {s.business_line for s in session.staff if s.business_line}
    project_lines = {p.business_line for p in session.projects if p.business_line}
    unmatched = project_lines - staff_lines
    if unmatched:
        issues.append(f"⚠️ 项目业务线无对应员工: {unmatched}（【暂不考虑】，不影响生成）")

    return issues


async def _generate(session, progress_label, result_label) -> None:
    if not session.can_generate:
        ui.notify("请先设定区间、添加员工和项目", type="warning")
        return
    progress_label.text = "正在生成..."
    result_label.text = ""
    try:
        span = session.global_span
        assert span is not None
        staff_states = [StaffState.from_info(s, span) for s in session.staff]

        # Resolve: empty/pending associated_person_ids → all staff; None dates → global span
        all_staff_ids = [s.name for s in session.staff]
        projects_to_gen = []
        for p in session.projects:
            # Replace empty/pending associated_person_ids with all staff
            pids = (
                all_staff_ids
                if not p.associated_person_ids or p.associated_person_ids == ["__pending__"]
                else p.associated_person_ids
            )
            # Replace None dates with global span
            sd = p.start_date if p.start_date is not None else span.start_date
            ed = p.end_date if p.end_date is not None else span.end_date
            projects_to_gen.append(
                Project(
                    id=p.id,
                    name=p.name,
                    start_date=sd,
                    end_date=ed,
                    target_ratio=p.target_ratio,
                    required_job_types=p.required_job_types,
                    associated_person_ids=pids,
                    ramp_up_point=p.ramp_up_point,
                    maintenance_point=p.maintenance_point,
                    business_line=p.business_line,
                )
            )
        cache = HolidayCache(_get_cache_dir())
        orch = HolidayOrchestrator(cache=cache)
        years = range(span.start_date.year, span.end_date.year + 1)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result_box: list = []

                def _run():
                    new_loop = asyncio.new_event_loop()
                    resolver = new_loop.run_until_complete(orch.ensure_years(*years))
                    result_box.append(resolver)
                    new_loop.close()

                t = threading.Thread(target=_run)
                t.start()
                t.join()
                resolver = result_box[0]
            else:
                resolver = loop.run_until_complete(orch.ensure_years(*years))
        except RuntimeError:
            resolver = asyncio.run(orch.ensure_years(*years))

        holidays: set[date] = set()
        session.holiday_fallback = resolver.is_fallback

        result = generate_with_retry(
            projects=projects_to_gen,
            staff_states=staff_states,
            holidays=holidays,
            global_span=span,
            max_retries=10,
            ratio_tolerance=RATIO_TOLERANCE,
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
                "⚠️ 节假日数据获取失败，已降级为仅周末排除",
                type="warning",
            )
    except Exception as e:
        progress_label.text = f"生成失败: {e}"
        ui.notify(f"生成失败: {e}", type="negative")


# --- Tab 5: Export (CSV only) ---
def _build_export(session: SessionState) -> None:
    ui.label("结果导出").classes("text-h6")
    ui.button("导出 CSV (工时记录)", on_click=lambda: _export_csv(session))


async def _export_csv(session) -> None:
    """Export work-hour records to CSV via browser download."""
    if not session.has_result:
        ui.notify("请先生成", type="warning")
        return
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".csv"))
    export_csv(session.generation_result.records, tmp)
    await _download_file(tmp.read_bytes(), filename="output.csv")


# --- Algorithm Info ---
def _build_algorithm_info() -> None:
    with ui.expansion("算法说明", icon="info").classes("q-mt-md w-full"):
        ui.markdown("""
### 生成逻辑说明

**两阶段贪心策略：**

1. **按项目分配人员**：按投入比例从低到高，为每个项目分配关联人员（允许一人多项目）。
2. **逐日填充工时**：对每个（项目，人员）对，逐日贪心分配工时。

**必然满足的条件（硬约束）：**
- ✅ 每人每天工时 ≤ 8h
- ✅ 1h 粒度分配
- ✅ 节假日无工时
- ✅ 投入比例在容差范围内

**尽量满足的条件（软目标）：**
- 🔄 相邻天同项目工时差 ≤ 2h（不跳来跳去）
- 🔄 每次连续投入 ≥ 3 天（spurt 约束）
- 🔄 自然抖动（避免机械整齐）

**暂不考虑的信息（MVP）：**
- 📌 业务线匹配（导入导出保留，生成不用）
- 📌 年假（MVP 默认 0）
- 📌 生命周期时间点（MVP 默认全期均匀）
- 📌 人事变更记录（MVP 默认全区间在职）

**总比例 < 1.0 时：** 每天不一定满载 8h，部分天为空闲（正常行为）。
**总比例 > 1.0 时：** 无法满足，生成报错。
""")


def _get_cache_dir() -> Path:
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
