# AGENTS.md — 环境与构建指引

> 本文件面向 AI agent 和人类开发者，讲清楚如何搭建环境、运行、测试、打包本项目。

## 项目概述

- **语言**: Python ≥ 3.14
- **框架**: [NiceGUI](https://nicegui.io) — 基于浏览器的 Python GUI 框架，支持 native window 模式
- **打包**: PyInstaller（`--isolated --no-dev` 隔离环境构建，排除 dev 依赖），输出单文件或目录型二进制
- **包管理**: [uv](https://docs.astral.sh/uv/) — 全部依赖管理、虚拟环境、脚本执行都通过 uv

## 环境搭建

### 前置要求

- **uv** ≥ 0.11 — 安装: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Python 3.14** — uv 会自动下载（`uv sync` 时按 `.python-version` 自动安装）

### 初始化

```bash
uv sync          # 创建 .venv 并安装全部依赖（含 dev group）
```

不需要手动 `python -m venv` 或 `pip install`，uv 全部接管。

### 日常命令

```bash
uv run nicegui-demo              # 启动应用（native window 模式）
uv run python main.py            # 等效，直接跑 main.py
uv run pytest                    # 运行测试
uv run ruff check .              # lint
uv run ruff format .             # 格式化
uv run python tools/icons.py logo.png  # 从图片生成三平台图标
```

> **始终用 `uv run` 前缀执行命令**，确保在项目虚拟环境内运行。

## 项目结构

```
.
├── main.py                          # PyInstaller 打包入口（freeze_support + ui.run）
├── pyproject.toml                   # 项目元数据、依赖、工具配置
├── src/nicegui_demo/
│   ├── __init__.py                  # build_ui() — UI 构建逻辑（无副作用，可 import 复用）
│   └── __main__.py                  # 控制台脚本入口（与 main.py 共享逻辑）
├── tools/
│   └── icons.py                     # 图标生成工具（开发用，不打包进二进制）
├── assets/app_icon/                 # 图标文件（由 tools/icons.py 生成，build.sh 自动引用）
├── tests/
│   ├── conftest.py                  # 注册 nicegui.testing 插件
│   └── test_ui.py                   # UI 测试（user_simulation，无需真实浏览器）
├── scripts/
│   └── build.sh                     # 打包脚本（nicegui-pack，隔离环境排除 dev 依赖）
└── .github/workflows/build.yml      # 多平台 CI 构建矩阵
```

## 关键设计决策

### main.py vs `__main__.py`

- `main.py`（项目根）是 PyInstaller/Nuitka 的打包目标。它委托给 `nicegui_demo.__main__:main`，确保打包二进制和控制台脚本行为一致。
- `src/nicegui_demo/__main__.py` 包含实际逻辑：`freeze_support()` + `ui.run()`。
- `src/nicegui_demo/__init__.py` 只含 `build_ui()`，纯 UI 构建函数，无副作用，可在测试和 FastAPI 嵌入中复用。

### `freeze_support()` 的位置

打包 native mode 应用时，`freeze_support()` **必须是 `if __name__ == "__main__"` 块的第一条语句**，否则 PyInstaller 打包后会产生无限进程循环。

`app.native` 配置（如 `window_args`）必须定义在 main guard **外部**，这样 `freeze_support` 拦截子进程前配置已生效。

```python
# ✅ 正确
app.native.window_args["resizable"] = True  # 外部

if __name__ == "__main__":
    freeze_support()                         # 内部第一条
    ui.run(native=True, reload=False)

# ❌ 错误 — native 配置会被子进程忽略
if __name__ == "__main__":
    app.native.window_args["resizable"] = True
    freeze_support()
    ui.run(native=True, reload=False)
```

### `reload=False` 和 `find_open_port()`

打包时必须 `reload=False`（PyInstaller 不支持热重载）。`native.find_open_port()` 扫描 8000-8999 端口，允许同一二进制多实例并行运行。

### 排除 dev 依赖

`uv sync` 把 dev group（Pillow、pytest、ruff、PyInstaller）装进同一个 `.venv`，PyInstaller 扫描 site-packages 时会把它们也打进去。`build.sh` 通过 `uv run --no-dev --isolated --with pyinstaller` 在干净的临时环境中构建：`--no-dev` 排除所有 dev 依赖，`--isolated` 创建临时 venv（不污染项目 .venv），`--with pyinstaller` 把构建工具加回来。PyInstaller 在隔离环境中根本看不到 dev 依赖，无需手动 `--exclude-module`。

## 打包

### 本地打包

```bash
uv run bash scripts/build.sh                       # onedir, 浏览器模式
uv run bash scripts/build.sh --native              # onedir, native window
uv run bash scripts/build.sh --onefile             # 单文件, 浏览器模式
uv run bash scripts/build.sh --native --onefile    # 单文件, native window
```

### 产物说明

| 模式 | 产物 | 启动速度 | 分发方式 |
|---|---|---|---|
| `--onedir` | `dist/nicegui-demo/` 目录 | 快 | 打成 zip 分发 |
| `--onefile` | `dist/nicegui-demo` 单文件 | 慢（每次解压临时目录） | 直接发送 |
| `+ --native` (macOS) | 额外生成 `dist/nicegui-demo.app` | 同上 | 双击打开 |

### macOS 注意事项

- `--onefile --windowed` 组合在 PyInstaller 7.0 将变成 error，推荐用 `--onedir --windowed`。
- `--windowed` 在 macOS 生成 `.app` bundle，无终端控制台。

### 平台差异

| | macOS | Windows | Linux |
|---|---|---|---|
| pywebview backend | WebKit（系统自带） | EdgeChromium (WebView2) | WebKitGTK |
| 前置系统依赖 | 无 | .NET Framework（通常预装） | `libgtk-3-0` `libwebkit2gtk-4.1-0` 等 |
| `--windowed` 效果 | 生成 `.app` | 无控制台弹窗 | 无终端 |

### 应用图标

图标分两个层面，两者都需要配置才能让 Dock 栏、任务栏和窗口内图标都生效：

| 层面 | 配置位置 | 作用 | 平台格式 |
|---|---|---|---|
| 二进制/Dock/任务栏图标 | `scripts/build.sh` 自动检测 `assets/app_icon/` | PyInstaller `--icon` 嵌入可执行文件和 `.app` bundle | macOS: `.icns`，Windows: `.ico`，Linux: `.png` |
| 窗口内 favicon | `src/nicegui_demo/__main__.py` 的 `ui.run(favicon=...)` | 浏览器标签页 / native 窗口标题栏图标 | 通用 `.png`；Windows native 需 `.ico` |

需要的图标文件：
```
assets/app_icon/
├── icon.icns    # macOS — PyInstaller --icon
├── icon.ico     # Windows — PyInstaller --icon + Windows native favicon
└── icon.png     # Linux — PyInstaller --icon + 通用 favicon
```

`build.sh` 会按当前平台自动选择对应图标文件并传给 `--icon`，同时通过 `--add-data` 把 `icon.png` 打包进 `assets/app_icon/` 供 `ui.run(favicon=...)` 运行时引用。缺文件时打印警告并继续构建（无自定义图标）。

> Windows native mode 下，`ui.run(favicon="assets/app_icon/icon.ico")` 的 `.ico` 路径会同时被用作 native 窗口图标（任务栏、标题栏）。

#### 从任意图片生成图标
项目内置了图标生成工具 `tools/icons.py`（开发工具，不打包进二进制），接受任意图片（PNG/JPG/WebP 等，≥256×256，推荐 1024×1024）并自动生成三种平台格式：

```bash
uv run python tools/icons.py logo.png                              # 输出到 assets/app_icon/
uv run python tools/icons.py photo.jpg --output-dir assets/app_icon  # 显式指定输出目录
```

生成结果：
```
assets/app_icon/icon.png   — 1024×1024 PNG（Linux + 通用 favicon）
assets/app_icon/icon.ico   — 多分辨率 ICO (16/24/32/48/64/128/256，Windows）
assets/app_icon/icon.icns  — 1024×1024 ICNS（macOS）
```

源图太小（<256px）或文件不存在时工具会报错退出。生成后直接 `uv run bash scripts/build.sh --native` 重新打包即可生效。

### 架构兼容性

**PyInstaller 不做交叉编译。** arm64 上打的二进制只能跑在 arm64 上，x86_64 同理。

- 如需多架构分发：在各架构机器上分别构建（CI matrix 已配置）。
- macOS universal2（arm64 + x86_64 合体）理论可行（`--target-architecture universal2`），但依赖链的 C 扩展不一定有 universal2 wheel，实践中不推荐。

## CI / GitHub Actions

`.github/workflows/build.yml` 定义了多平台构建矩阵：

| Runner | OS | 架构 | 打包模式 |
|---|---|---|---|
| `macos-14` | macOS | arm64 (Apple Silicon) | onedir（启动快，`.app` bundle） |
| `macos-13` | macOS | x86_64 (Intel) | onedir（启动快，`.app` bundle） |
| `windows-latest` | Windows | x86_64 | onefile（单文件分发） |
| `ubuntu-22.04` | Linux | x86_64 | onefile（单文件分发） |

> macOS 用 onedir 避免每次启动解压到临时目录，冷启动更快；Windows/Linux 用 onefile，分发更简单。

**触发方式**：
- 推送 `v*` 标签 → 构建 + 自动创建 GitHub Release 并上传 zip 产物
- `workflow_dispatch` → 手动触发，仅构建不上传 Release

**本地验证 CI 逻辑**（不模拟跨平台，仅验证脚本和配置）：
```bash
uv run pytest && uv run ruff check . && uv run bash scripts/build.sh --native
```

### 发起一次发布

```bash
git tag v0.1.0
git push origin v0.1.0
# → CI 自动在 4 个平台构建，完成后在 Releases 页面生成下载
```

## 测试

测试使用 NiceGUI 的 `user_simulation` 上下文管理器（Python 层模拟，无需真实浏览器）：

- `tests/conftest.py` 注册 `nicegui.testing.user_plugin`，提供 `user` fixture。
- `tests/test_ui.py` 用 `async with user_simulation(root=build_ui) as user` 测试 UI 构建。
- `asyncio_mode = "auto"` 已在 `pyproject.toml` 中配置，无需手动加 `@pytest.mark.asyncio`（但写了也无害）。

如需测试完整的 `main.py` 运行路径，用 pytest marker：
```python
@pytest.mark.nicegui_main_file("main.py")
async def test_main_entry(user):
    await user.open("/")
```

## 常见问题

### `ModuleNotFoundError: No module named 'webview'`

native window 模式需要 pywebview：`uv add pywebview`。

### Linux 上 native 窗口启动报错

缺 WebKitGTK：`sudo apt install libgtk-3-0 libwebkit2gtk-4.1-0 libglib2.0-0`。

### PyInstaller 打包后无限启动子进程

`freeze_support()` 没有放在 `if __name__ == "__main__"` 的第一条语句。见上文「关键设计决策」。

### 打包后 `TypeError: a bytes-like object is required, not 'str'`

PyInstaller + Windows 的已知问题。在 `main.py` 顶部加：
```python
import sys
sys.stdout = open("logs.txt", "w")
```
参考 [nicegui#681](https://github.com/zauberzeug/nicegui/issues/681)。
