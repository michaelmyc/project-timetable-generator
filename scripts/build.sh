#!/usr/bin/env bash
# Build a binary from main.py using nicegui-pack (PyInstaller).
#
# Usage:
#   uv run bash scripts/build.sh              # onedir, browser mode
#   uv run bash scripts/build.sh --native      # onedir + native window
#   uv run bash scripts/build.sh --onefile     # single-file, browser mode
#   uv run bash scripts/build.sh --native --onefile  # single-file + native window
#
# Output: dist/nicegui-demo (onedir dir or onefile executable)
#         dist/nicegui-demo.app (macOS with --native, .app bundle)
#
# Icon files (auto-detected by platform, under assets/app_icon/):
#   assets/app_icon/icon.icns  → macOS
#   assets/app_icon/icon.ico   → Windows
#   assets/app_icon/icon.png   → Linux (also used as favicon in code)
set -euo pipefail

cd "$(dirname "$0")/.."

MODE="--onedir"
NATIVE_ARG=""
for arg in "$@"; do
  case "$arg" in
    --onefile)  MODE="--onefile" ;;
    --native)   NATIVE_ARG="--windowed" ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

ICON_DIR="assets/app_icon"

# Pick the platform-appropriate icon for PyInstaller (binary/Dock/taskbar icon).
ICON_ARGS=""
case "$(uname -s)" in
  Darwin) ICON_FILE="${ICON_DIR}/icon.icns" ;;
  Linux)  ICON_FILE="${ICON_DIR}/icon.png" ;;
  MINGW*|MSYS*|CYGWIN*) ICON_FILE="${ICON_DIR}/icon.ico" ;;
esac
if [[ -n "${ICON_FILE:-}" && -f "$ICON_FILE" ]]; then
  ICON_ARGS="--icon $ICON_FILE"
else
  echo "Warning: icon file not found ($ICON_FILE); building without a custom icon." >&2
fi

# Path separator for PyInstaller --add-data: ';' on Windows, ':' elsewhere.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) SEP=";" ;;
  *) SEP=":" ;;
esac

# Bundle the favicon PNG so `ui.run(favicon=...)` can find it at runtime.
DATA_ARGS=""
if [[ -f "${ICON_DIR}/icon.png" ]]; then
  DATA_ARGS="--add-data ${ICON_DIR}/icon.png${SEP}${ICON_DIR}"
fi

# Build in a clean ephemeral environment with ONLY runtime deps + pyinstaller.
# `--isolated` creates a temporary venv so dev-only packages (pytest, ruff,
# Pillow) never enter the picture and PyInstaller cannot discover or bundle them.
# `--with pyinstaller` adds the build tool on top of runtime deps.
uv run --no-dev --isolated --with pyinstaller nicegui-pack \
  "$MODE" \
  --name "nicegui-demo" \
  --clean \
  --noconfirm \
  $NATIVE_ARG \
  $ICON_ARGS \
  $DATA_ARGS \
  main.py

echo "Build complete → dist/nicegui-demo"
