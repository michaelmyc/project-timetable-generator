"""Tests for UI build — verify the page renders with expected elements."""

from nicegui.testing import user_simulation


async def test_page_loads(user: user_simulation):
    await user.open("/")
    await user.should_see("排班打卡时间表生成器")


async def test_page_has_global_span_tab(user: user_simulation):
    await user.open("/")
    await user.should_see("区间设置")


async def test_page_has_staff_management(user: user_simulation):
    await user.open("/")
    await user.should_see("员工管理")
    await user.should_see("添加员工")


async def test_page_has_project_management(user: user_simulation):
    await user.open("/")
    await user.should_see("项目管理")
    await user.should_see("添加项目")


async def test_page_has_validate_and_generate_button(user: user_simulation):
    await user.open("/")
    await user.should_see("校验与生成")


async def test_page_has_export_tab(user: user_simulation):
    await user.open("/")
    await user.should_see("结果导出")


async def test_page_has_algorithm_info(user: user_simulation):
    await user.open("/")
    await user.should_see("算法说明")
