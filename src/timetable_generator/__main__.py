"""Console script entry point — shared with PyInstaller main.py."""

import multiprocessing

from nicegui import app, ui

from timetable_generator.ui.app import build_ui

app.native.window_args["resizable"] = True
app.native.start_args["debug"] = False


@ui.page("/")
def index() -> None:
    """Main page — builds the timetable generator UI."""
    build_ui()


def main() -> None:
    """Run the timetable generator UI in native window mode."""
    ui.run(
        title="排班打卡时间表生成器",
        reload=False,
        port=8080,
        native=True,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
