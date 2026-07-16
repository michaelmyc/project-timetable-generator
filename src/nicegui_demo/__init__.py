"""NiceGUI demo application package.

UI construction lives here so it can be imported and reused. The runnable
entry point (with `freeze_support` and `ui.run`) lives in `main.py` at the
project root, which is the target `nicegui-pack` / PyInstaller bundles.
"""

from __future__ import annotations

from nicegui import ui


def build_ui() -> None:
    """Construct the demo UI.

    Kept side-effect-free (no `ui.run`) so it can be imported in tests or
    embedded into an existing FastAPI app without starting a server.
    """
    ui.label("NiceGUI Demo").classes("text-2xl font-bold")
    ui.button("Click me", icon="thumb_up", on_click=lambda: ui.notify("Hello!"))


__all__ = ["build_ui"]
