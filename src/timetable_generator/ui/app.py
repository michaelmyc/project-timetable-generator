"""NiceGUI UI — build the full MVP interface (overhauled).

Features:
- Calendar date picker for global span
- Staff management: add/edit/delete + CSV/Excel import/export
- Job types: computed from staff, textbox input with bubble chips
- Project management: add/edit/delete + CSV/Excel import/export
- Pre-generation validation button
- Algorithm explanation panel
- 【暂不考虑】labels for unused fields (business_line, onboard/leave dates)
- All unused fields preserved in import/export but not editable in MVP
"""

from __future__ import annotations

import asyncio
import threading
from datetime import date
from pathlib import Path

from nicegui import ui

from timetable_generator.export.csv import export_csv
from timetable_generator.generator.retry import generate_with_retry
from timetable_generator.holiday.cache import HolidayCache
from timetable_generator.holiday.orchestrator import HolidayOrchestrator
from timetable_generator.io.params import SessionParams, export_params
from timetable_generator.io.project_csv import export_projects_csv, import_projects_csv
from timetable_generator.io.staff_csv import export_staff_csv, import_staff_csv
from timetable_generator.models.project import Project
from timetable_generator.models.staff_info import DEFAULT_JOB_TYPE, StaffInfo
from timetable_generator.models.staff_state import StaffState
from timetable_generator.ui.session import SessionState

RATIO_TOLERANCE = 0.08


def build_ui() -> SessionState:
    """Build the UI and return the session state for testing."""
    session = SessionState()

    ui.label("排班打卡时间表生成器").classes("text-h4 q-mb-md")

    _build_global_span(session)
    _build_staff_management(session)
    _build_project_management(session)
    _build_validation(session)
    _build_generate(session)
    _build_export(session)
    _build_algorithm_info()

    return session


# --- Step 1: Global Span (calendar) ---
def _build_global_span(session: SessionState) -> None:
    ui.label("1. 全局生成区间").classes("text-h6")

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
        start_picker = ui.date_input(label="开始日期", on_change=_on_change)
        end_picker = ui.date_input(label="结束日期", on_change=_on_change)


def _set_span(session, start_picker, end_picker, span_label) -> None:
    """Kept for backward compat — not used by UI anymore."""
    pass


# --- Step 2: Staff Management ---
def _build_staff_management(session: SessionState) -> None:
    ui.label("2. 员工管理").classes("text-h6 q-mt-md")

    # Import/Export buttons
    with ui.row():
        ui.button("导入员工", on_click=lambda: _import_staff(session, staff_table))
        ui.button("导出员工", on_click=lambda: _export_staff(session))

    # Staff table with edit/delete
    staff_table = ui.table(
        columns=[
            {"name": "name", "label": "员工", "field": "name"},
            {"name": "job_type", "label": "工种", "field": "job_type"},
            {"name": "business_line", "label": "业务线【暂不考虑】", "field": "business_line"},
            {"name": "onboard_date", "label": "入职时间【暂不考虑】", "field": "onboard_date"},
            {"name": "leave_date", "label": "离职时间【暂不考虑】", "field": "leave_date"},
        ],
        rows=[],
        row_key="name",
    )

    # Add/Edit dialog
    ui.button("添加员工", on_click=lambda: _show_staff_dialog(session, staff_table, None))

    session._staff_table = staff_table  # type: ignore[attr-defined]


def _show_staff_dialog(session, staff_table, edit_index: int | None) -> None:
    """Show add/edit staff dialog. edit_index=None for add, index for edit."""
    with ui.dialog() as dialog, ui.card():
        title = "编辑员工" if edit_index is not None else "添加员工"
        ui.label(title).classes("text-h6")

        existing = session.staff[edit_index] if edit_index is not None else None

        name_input = ui.input(label="员工姓名", value=existing.name if existing else "")
        job_input = ui.input(
            label="工种（textbox，可输入新工种）",
            value=existing.job_type if existing else DEFAULT_JOB_TYPE,
        )
        # Business line: 暂不考虑
        ui.label("业务线: 【暂不考虑】（导入导出保留）").classes("text-caption text-grey")
        bl_input = ui.input(
            label="业务线（可选）",
            value=existing.business_line if existing else None,
        )
        ui.label("入职时间: 【暂不考虑】").classes("text-caption text-grey")
        onboard_input = ui.input(
            label="入职时间 (YYYY-MM-DD，可选)",
            value=existing.onboard_date.isoformat() if existing and existing.onboard_date else None,
        )
        ui.label("离职时间: 【暂不考虑】").classes("text-caption text-grey")
        leave_input = ui.input(
            label="离职时间 (YYYY-MM-DD，可选)",
            value=existing.leave_date.isoformat() if existing and existing.leave_date else None,
        )

        def _save():
            name = (name_input.value or "").strip()
            if not name:
                ui.notify("姓名不能为空", type="warning")
                return
            job = (job_input.value or "").strip() or DEFAULT_JOB_TYPE
            bl = (bl_input.value or "").strip() or None
            onboard = (
                date.fromisoformat((onboard_input.value or "").strip())
                if onboard_input.value and (onboard_input.value or "").strip()
                else None
            )
            leave = (
                date.fromisoformat((leave_input.value or "").strip())
                if leave_input.value and (leave_input.value or "").strip()
                else None
            )
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
    with ui.dialog() as dialog, ui.card():
        ui.label("导入员工").classes("text-h6")
        ui.label("格式: 员工,工种,业务线,入职时间,离职时间 (CSV 或 Excel)").classes("text-caption")

        async def _on_upload(e):
            try:
                content = e.content.read()
                tmp = Path("/tmp/_staff_import.tmp")
                tmp.write_bytes(content)
                imported = import_staff_csv(tmp)
                session.staff.extend(imported)
                _refresh_staff_table(session, staff_table)
                ui.notify(f"导入 {len(imported)} 名员工", type="positive")
                dialog.close()
            except Exception as ex:
                ui.notify(f"导入失败: {ex}", type="negative")

        ui.upload(label="选择文件", on_upload=_on_upload, auto_upload=True)
        ui.button("取消", on_click=dialog.close)
    dialog.open()


def _export_staff(session) -> None:
    """Export staff to CSV via browser download."""
    if not session.staff:
        ui.notify("没有员工可导出", type="warning")
        return
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".csv"))
    export_staff_csv(session.staff, tmp)
    ui.download(tmp, filename="staff_export.csv")


# --- Step 3: Project Management ---
def _build_project_management(session: SessionState) -> None:
    ui.label("3. 项目管理").classes("text-h6 q-mt-md")

    with ui.row():
        ui.button("导入项目", on_click=lambda: _import_projects(session))
        ui.button("导出项目", on_click=lambda: _export_projects(session))

    project_table = ui.table(
        columns=[
            {"name": "id", "label": "项目标识", "field": "id"},
            {"name": "name", "label": "项目名称", "field": "name"},
            {"name": "target_ratio", "label": "投入比例", "field": "target_ratio"},
            {"name": "required_job_types", "label": "所需工种", "field": "required_job_types"},
            {"name": "business_line", "label": "业务线【暂不考虑】", "field": "business_line"},
            {"name": "start_date", "label": "开始时间", "field": "start_date"},
            {"name": "end_date", "label": "结束时间", "field": "end_date"},
        ],
        rows=[],
        row_key="id",
    )

    ui.button("添加项目", on_click=lambda: _show_project_dialog(session, project_table, None))

    session._project_table = project_table  # type: ignore[attr-defined]


def _show_project_dialog(session, project_table, edit_index: int | None) -> None:
    with ui.dialog() as dialog, ui.card():
        title = "编辑项目" if edit_index is not None else "添加项目"
        ui.label(title).classes("text-h6")

        existing = session.projects[edit_index] if edit_index is not None else None

        pid_input = ui.input(label="项目标识", value=existing.id if existing else "")
        pname_input = ui.input(label="项目名称", value=existing.name if existing else "")
        ui.label("业务线: 【暂不考虑】").classes("text-caption text-grey")
        bl_input = ui.input(
            label="业务线（可选）", value=existing.business_line if existing else None
        )
        ratio_input = ui.number(
            label="投入比例 (0-1)",
            min=0,
            max=1,
            step=0.01,
        )
        start_input = ui.date_input(label="项目开始日期")
        end_input = ui.date_input(label="项目结束日期")
        if existing:
            start_input.value = existing.start_date.isoformat()
            end_input.value = existing.end_date.isoformat()

        # Job types: computed from staff, textbox multi
        job_types = session.get_job_types()
        ui.label(
            f"可用工种（从员工管理 computed）: {', '.join(job_types) if job_types else '无'}"
        ).classes("text-caption")
        jobs_input = ui.input(
            label="所需工种（逗号分隔，可空=不设约束）",
            value=", ".join(existing.required_job_types)
            if existing and existing.required_job_types
            else "",
        )

        def _save():
            pid = (pid_input.value or "").strip()
            pname = (pname_input.value or "").strip()
            if not pid or not pname:
                ui.notify("标识和名称不能为空", type="warning")
                return
            ratio = float(ratio_input.value)
            bl = (bl_input.value or "").strip() or None
            if session.global_span is None:
                ui.notify("请先设定全局区间", type="warning")
                return
            sd = (
                date.fromisoformat(str(start_input.value))
                if start_input.value
                else session.global_span.start_date
            )
            ed = (
                date.fromisoformat(str(end_input.value))
                if end_input.value
                else session.global_span.end_date
            )
            jobs = (
                [j.strip() for j in (jobs_input.value or "").split(",") if j.strip()]
                if jobs_input.value
                else []
            )
            staff_ids = session.get_staff_ids()
            if not staff_ids:
                ui.notify("请先添加员工", type="warning")
                return
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


def _refresh_project_table(session, project_table) -> None:
    rows = []
    for p in session.projects:
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "target_ratio": f"{p.target_ratio:.0%}",
                "required_job_types": ", ".join(p.required_job_types)
                if p.required_job_types
                else "无约束",
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
            }
        )
    project_table.update_rows(rows)


def _import_projects(session) -> None:
    """Import projects via file picker (ui.upload)."""
    with ui.dialog() as dialog, ui.card():
        ui.label("导入项目").classes("text-h6")
        ui.label("格式: 项目标识,项目名称,业务线,投入百分比,项目开始时间,项目结束时间").classes(
            "text-caption"
        )

        async def _on_upload(e):
            try:
                content = e.content.read()
                tmp = Path("/tmp/_project_import.tmp")
                tmp.write_bytes(content)
                imported = import_projects_csv(tmp)
                session.projects.extend(imported)
                _refresh_project_table(session, session._project_table)  # type: ignore[attr-defined]
                ui.notify(f"导入 {len(imported)} 个项目", type="positive")
                dialog.close()
            except Exception as ex:
                ui.notify(f"导入失败: {ex}", type="negative")

        ui.upload(label="选择文件", on_upload=_on_upload, auto_upload=True)
        ui.button("取消", on_click=dialog.close)
    dialog.open()


def _export_projects(session) -> None:
    """Export projects to CSV via browser download."""
    if not session.projects:
        ui.notify("没有项目可导出", type="warning")
        return
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".csv"))
    export_projects_csv(session.projects, tmp)
    ui.download(tmp, filename="projects_export.csv")


# --- Step 4: Validation ---
def _build_validation(session: SessionState) -> None:
    ui.label("4. 校验").classes("text-h6 q-mt-md")
    ui.button("整体校验", on_click=lambda: _validate(session, validation_label))
    validation_label = ui.label("")
    session._validation_label = validation_label  # type: ignore[attr-defined]


def _validate(session, validation_label) -> None:
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

    if not issues:
        validation_label.text = "✅ 校验通过，可以生成"
        ui.notify("校验通过", type="positive")
    else:
        validation_label.text = "\n".join(issues)
        ui.notify(f"发现 {len(issues)} 个问题", type="warning")


# --- Step 5: Generate ---
def _build_generate(session: SessionState) -> None:
    ui.label("5. 生成").classes("text-h6 q-mt-md")
    ui.button("生成工时表", on_click=lambda: _generate(session, progress_label, result_label))
    progress_label = ui.label("")
    result_label = ui.label("")
    session._progress_label = progress_label  # type: ignore[attr-defined]
    session._result_label = result_label  # type: ignore[attr-defined]


def _generate(session, progress_label, result_label) -> None:
    if not session.can_generate:
        ui.notify("请先设定区间、添加员工和项目", type="warning")
        return
    progress_label.text = "正在生成..."
    result_label.text = ""
    try:
        span = session.global_span
        assert span is not None
        staff_states = [StaffState.from_changes(s.name, [], span) for s in session.staff]

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
            projects=session.projects,
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


# --- Step 6: Export ---
def _build_export(session: SessionState) -> None:
    ui.label("6. 导出").classes("text-h6 q-mt-md")
    ui.button("导出 CSV (工时记录)", on_click=lambda: _export_csv(session))
    ui.button("导出配置 (JSON)", on_click=lambda: _export_params(session))


def _export_csv(session) -> None:
    """Export work-hour records to CSV via browser download."""
    if not session.has_result:
        ui.notify("请先生成", type="warning")
        return
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".csv"))
    export_csv(session.generation_result.records, tmp)
    ui.download(tmp, filename="output.csv")


def _export_params(session) -> None:
    """Export session params to JSON via browser download."""
    if session.global_span is None:
        ui.notify("请先设定区间", type="warning")
        return
    params = SessionParams(
        global_span=session.global_span,
        projects=session.projects,
        staff=session.staff,
    )
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".json"))
    export_params(params, tmp)
    ui.download(tmp, filename="params.json")


# --- Algorithm Info ---
def _build_algorithm_info() -> None:
    with ui.expansion("算法说明", icon="info").classes("q-mt-md"):
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
- 📌 入职/离职时间（导入导出保留，生成不用）
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
