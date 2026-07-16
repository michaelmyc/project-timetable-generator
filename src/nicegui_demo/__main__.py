"""Console-script entry point.

Mirrors the root `main.py` so `uv run nicegui-demo` and the packaged binary
behave identically. When packaged with PyInstaller, the root `main.py` is the
target instead, but both share the same logic via `build_ui`.
"""

from __future__ import annotations

from multiprocessing import freeze_support

from nicegui import app, native, ui

from nicegui_demo import build_ui

# Native window configuration MUST live outside the main guard so it is
# applied before `freeze_support()` intercepts the spawned subprocess.
app.native.window_args["resizable"] = True


def main() -> None:
    freeze_support()
    ui.run(
        root=build_ui,
        reload=False,
        native=True,
        port=native.find_open_port(),
        title="NiceGUI Demo",
        favicon="assets/app_icon/icon.png",
    )


if __name__ == "__main__":
    main()
