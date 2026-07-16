"""Pytest configuration shared by all tests.

Registers NiceGUI's testing fixtures (`user`, `create_user`) and the
`nicegui_main_file` marker. The `main_file` ini option defaults to `main.py`
(declared by the plugin's `pytest_addoption`) so the `user` fixture runs the
same entry point that gets packaged.
"""

pytest_plugins = ["nicegui.testing.user_plugin"]
