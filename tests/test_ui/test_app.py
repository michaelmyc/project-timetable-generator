"""Tests for UI build — verify the page renders with expected elements."""

from nicegui.testing import user_simulation


async def test_page_loads(user: user_simulation):
    """Page should load and show title."""
    await user.open("/")
    await user.should_see("排班打卡时间表生成器")


async def test_page_has_global_span_inputs(user: user_simulation):
    await user.open("/")
    await user.should_see("全局生成区间")


async def test_page_has_staff_section(user: user_simulation):
    await user.open("/")
    await user.should_see("员工名单")


async def test_page_has_project_section(user: user_simulation):
    await user.open("/")
    await user.should_see("项目批次")


async def test_page_has_generate_button(user: user_simulation):
    await user.open("/")
    await user.should_see("生成工时表")


async def test_page_has_export_buttons(user: user_simulation):
    await user.open("/")
    await user.should_see("导出 CSV")
