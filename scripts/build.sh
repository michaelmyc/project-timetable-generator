#!/usr/bin/env bash
# Build a binary from main.py using nicegui-pack (PyInstaller).
#
# Usage:
#   uv run bash scripts/build.sh              # auto: macOS=onedir .app, Windows/Linux=onefile
#   uv run bash scripts/build.sh --native     # + native window (--windowed)
#   uv run bash scripts/build.sh --onedir     # force onedir (all platforms)
#   uv run bash scripts/build.sh --onefile    # force onefile (all platforms)
#
# Output:
#   macOS onedir + --native → dist/timetable-generator.app (double-clickable)
#   Windows onefile          → dist/timetable-generator.exe (single file)
#   Linux  onefile           → dist/timetable-generator (single file)
#
# Icon files (auto-detected by platform, under assets/app_icon/):
#   assets/app_icon/icon.icns  → macOS
#   assets/app_icon/icon.ico   → Windows
#   assets/app_icon/icon.png   → Linux
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="timetable-generator"
NATIVE_ARG=""

# Default mode by platform: macOS = onedir, Windows/Linux = onefile
case "$(uname -s)" in
  Darwin) MODE="--onedir" ;;
  *)      MODE="--onefile" ;;
esac

for arg in "$@"; do
  case "$arg" in
    --onefile)  MODE="--onefile" ;;
    --onedir)   MODE="--onedir" ;;
    --native)   NATIVE_ARG="--windowed" ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

ICON_DIR="assets/app_icon"

# Pick the platform-appropriate icon for PyInstaller.
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

echo "Building $APP_NAME: mode=$MODE, native=$([[ -n "$NATIVE_ARG" ]] && echo yes || echo no)"

# Build in a clean ephemeral environment with ONLY runtime deps + pyinstaller.
uv run --no-dev --isolated --with pyinstaller nicegui-pack \
  "$MODE" \
  --name "$APP_NAME" \
  --clean \
  --noconfirm \
  $NATIVE_ARG \
  $ICON_ARGS \
  $DATA_ARGS \
  main.py

echo "Build complete → dist/$APP_NAME"
