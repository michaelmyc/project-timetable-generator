"""Entry point for PyInstaller and nicegui testing.

Run mode:
  uv run python main.py              # web server (browser, default, for debugging)
  uv run python main.py --native     # native window (pywebview)
  uv run python main.py --port 9000  # custom port
"""

import sys

import multiprocessing

from nicegui import app, ui

from timetable_generator.ui.app import build_ui

# Native window config must be set before the main guard (AGENTS.md).
app.native.window_args["resizable"] = True
app.native.start_args["debug"] = False


@ui.page("/")
def index() -> None:
    """Main page — builds the timetable generator UI."""
    build_ui()


def main() -> None:
    """Run the timetable generator UI."""
    native = "--native" in sys.argv
    port = 8080
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    ui.run(
        title="排班打卡时间表生成器",
        reload=False,
        port=port,
        native=native,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
