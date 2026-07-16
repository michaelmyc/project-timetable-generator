"""Entry point for PyInstaller and nicegui testing."""

import multiprocessing

from nicegui import ui

from timetable_generator.ui.app import build_ui


@ui.page("/")
def index() -> None:
    """Main page — builds the timetable generator UI."""
    build_ui()


def main() -> None:
    """Run the timetable generator UI."""
    ui.run(title="排班打卡时间表生成器", reload=False, port=8080)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
