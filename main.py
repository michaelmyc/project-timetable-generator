"""Runnable entry point and PyInstaller/Nuitka target.

`nicegui-pack --onefile --name nicegui-demo main.py` bundles this file.
It delegates to `nicegui_demo.__main__:main` so the console script and the
packaged binary share a single implementation.

Run directly with:  uv run python main.py
"""

from __future__ import annotations

from nicegui_demo.__main__ import main

if __name__ == "__main__":
    main()
