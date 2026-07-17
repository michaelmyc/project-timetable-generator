"""Tests for UI build — verify the page renders with expected elements."""

from nicegui.testing import user_simulation

from timetable_generator.ui.app import build_ui


async def test_page_loads(user: user_simulation):
    await user.open("/")
    await user.should_see("排班打卡时间表生成器")


async def test_page_has_global_span_calendar(user: user_simulation):
    await user.open("/")
    await user.should_see("全局生成区间")


async def test_page_has_staff_management(user: user_simulation):
    await user.open("/")
    await user.should_see("员工管理")
    await user.should_see("添加员工")


async def test_page_has_project_management(user: user_simulation):
    await user.open("/")
    await user.should_see("项目管理")
    await user.should_see("添加项目")


async def test_page_has_validation_button(user: user_simulation):
    await user.open("/")
    await user.should_see("整体校验")


async def test_page_has_generate_button(user: user_simulation):
    await user.open("/")
    await user.should_see("生成工时表")


async def test_page_has_export_buttons(user: user_simulation):
    await user.open("/")
    await user.should_see("导出 CSV")


async def test_page_has_algorithm_info(user: user_simulation):
    await user.open("/")
    await user.should_see("算法说明")
