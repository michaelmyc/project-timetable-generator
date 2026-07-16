"""Tests for the demo UI builder.

Uses NiceGUI's `user_simulation` context manager with `root=build_ui` directly,
which is fast (no real browser). For testing the full `main.py` run path,
register the `nicegui.testing.user_plugin` pytest plugin and use the
`@pytest.mark.nicegui_main_file("main.py")` marker on the test.
"""

from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.testing import user_simulation

from nicegui_demo import build_ui


@pytest.mark.asyncio
async def test_build_ui_creates_label_and_button() -> None:
    """build_ui should add a label and a button to the page."""
    async with user_simulation(root=build_ui) as user:
        await user.open("/")
        await user.should_see(ui.label)
        await user.should_see(ui.button)


@pytest.mark.asyncio
async def test_button_click_sends_notification() -> None:
    """Clicking the button should trigger a 'Hello!' notification."""
    async with user_simulation(root=build_ui) as user:
        await user.open("/")
        user.find(ui.button).click()
        assert user.notify.contains("Hello!")
