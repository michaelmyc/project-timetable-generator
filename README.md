# NiceGUI Demo

一个基于 [NiceGUI](https://nicegui.io) 的桌面应用模板，使用 [uv](https://docs.astral.sh/uv/) 管理依赖，通过 PyInstaller 打包为跨平台二进制（macOS / Windows / Linux）。

## 功能

- 原生窗口模式（pywebview），弹出独立窗口而非浏览器标签
- 从任意图片一键生成三平台应用图标
- 多平台 CI 自动构建 + GitHub Release 发布
- 内置测试框架（`pytest` + `nicegui.testing`，无需真实浏览器）

## 快速开始

### 环境要求

- [uv](https://docs.astral.sh/uv/) ≥ 0.11 — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Python 3.14+（uv 自动安装，无需手动操作）

### 安装与运行

```bash
uv sync                # 创建虚拟环境并安装全部依赖
uv run nicegui-demo    # 启动应用（独立窗口）
```

### 测试

```bash
uv run pytest          # 运行测试
uv run ruff check .    # 代码检查
```

## 设置应用图标

### 从任意图片生成

```bash
uv run python tools/icons.py logo.png
# → assets/app_icon/icon.png   (1024×1024 PNG)
# → assets/app_icon/icon.ico   (多分辨率 ICO: 16/24/32/48/64/128/256)
# → assets/app_icon/icon.icns  (1024×1024 ICNS)
```

- 源图片支持 PNG / JPG / WebP 等任意格式
- 最小 256×256，推荐 1024×1024（高分辨率源图缩放效果更好）
- 支持 RGBA 透明通道

生成后重新打包即可生效，代码和脚本无需改动。

### 图标的作用

| 文件 | 平台 | 作用 |
|---|---|---|
| `icon.icns` | macOS | Dock 栏图标、`.app` bundle 图标 |
| `icon.ico` | Windows | 任务栏图标、可执行文件图标、native 窗口图标 |
| `icon.png` | 全平台 | 浏览器标签页 favicon / native 窗口标题栏图标 |

## 打包为二进制

### 本地打包

```bash
uv run bash scripts/build.sh              # onedir，浏览器模式
uv run bash scripts/build.sh --native      # onedir，原生窗口（推荐 macOS）
uv run bash scripts/build.sh --onefile     # 单文件，浏览器模式
uv run bash scripts/build.sh --native --onefile  # 单文件，原生窗口
```

打包脚本会自动检测 `assets/app_icon/` 下对应平台的图标文件并嵌入。

### 产物

| 模式 | 产物 | 启动速度 | 分发方式 |
|---|---|---|---|
| `--onedir` | `dist/nicegui-demo/` 目录 | 快 | 打成 zip 分发 |
| `--onefile` | `dist/nicegui-demo` 单文件 | 慢（每次解压到临时目录） | 直接发送 |
| `+ --native` (macOS) | 额外生成 `dist/nicegui-demo.app` | 同上 | 双击打开 |

> macOS 推荐用 `--onedir --native`：启动快，无 PyInstaller 7.0 兼容警告。

### 平台差异

| | macOS | Windows | Linux |
|---|---|---|---|
| 窗口引擎 | WebKit（系统自带） | EdgeChromium (WebView2) | WebKitGTK |
| 系统依赖 | 无 | .NET Framework（通常预装） | `libgtk-3-0` `libwebkit2gtk-4.1-0` 等 |
| 图标格式 | `.icns` | `.ico` | `.png` |

## CI 自动构建

项目配置了 GitHub Actions 多平台构建矩阵（`.github/workflows/build.yml`）：

| 平台 | 架构 | 打包模式 |
|---|---|---|
| macOS (Apple Silicon) | arm64 | onedir |
| macOS (Intel) | x86_64 | onedir |
| Windows | x86_64 | onefile |
| Linux | x86_64 | onefile |

### 发起发布

```bash
git tag v0.1.0
git push origin v0.1.0
# → CI 自动在 4 个平台并行构建，完成后在 Releases 页面生成下载
```

也可在 Actions 页面手动触发（`workflow_dispatch`），仅构建不发布。

## 项目结构

```
.
├── main.py                       # 打包入口（PyInstaller 目标）
├── pyproject.toml                # 项目配置、依赖、工具设置
├── src/nicegui_demo/
│   ├── __init__.py               # UI 构建逻辑
│   └── __main__.py               # 控制台脚本入口
├── tools/
│   └── icons.py                  # 图标生成工具（开发用，不打包）
├── assets/app_icon/              # 图标文件（tools/icons.py 生成）
├── tests/                        # 测试
├── scripts/build.sh              # 打包脚本
└── .github/workflows/build.yml   # CI 构建矩阵
```

## License

MIT
