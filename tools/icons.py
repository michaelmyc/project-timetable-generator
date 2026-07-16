"""Generate platform-specific app icons from a source image.

  assets/app_icon/icon.png   — 1024×1024 PNG (Linux PyInstaller icon + universal favicon)
  assets/app_icon/icon.ico   — multi-resolution ICO (Windows PyInstaller icon + native favicon)
  assets/app_icon/icon.icns  — Apple ICNS (macOS PyInstaller icon + Dock icon)

Requires Pillow (installed in dev group): `uv sync --dev`

Usage:
  uv run python tools/icons.py <source_image> [--output-dir assets/app_icon]

Examples:
  uv run python tools/icons.py logo.png
  uv run python tools/icons.py photo.jpg --output-dir assets/app_icon
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

# ICNS needs a 1024×1024 base image; Pillow handles the rest.
_ICNS_SIZE = 1024

# ICO: bundle multiple sizes for crisp rendering at all DPI levels.
_ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

# PNG favicon: 1024×1024 is a good high-res base; browsers/downsampling handle the rest.
_PNG_SIZE = 1024


def generate_icons(source: Path, output_dir: Path) -> dict[str, Path]:
    """Generate icon files from a source image.

    :param source: Path to the source image (any format Pillow can open).
    :param output_dir: Directory to write icon files into (created if missing).
    :returns: Dict mapping format name to output file path.
    :raises FileNotFoundError: If source image doesn't exist.
    :raises ValueError: If the image cannot be opened or is too small.
    """
    if not source.is_file():
        raise FileNotFoundError(f"Source image not found: {source}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as img:
        img = img.convert("RGBA")

        if max(img.size) < 256:
            raise ValueError(
                f"Source image too small ({img.size[0]}×{img.size[1]}). "
                f"Use at least 256×256, ideally 1024×1024."
            )

        generated: dict[str, Path] = {}

        # PNG — 1024×1024 base
        png_path = output_dir / "icon.png"
        img_resized = img.resize((_PNG_SIZE, _PNG_SIZE), Image.LANCZOS)
        img_resized.save(png_path, "PNG")
        generated["png"] = png_path

        # ICO — multi-resolution bundle.
        # Pillow auto-downscales from a single 256×256 base for each size in
        # `sizes`; a larger base is silently capped at 256 by the ICO spec.
        ico_path = output_dir / "icon.ico"
        ico_base = img.resize((256, 256), Image.LANCZOS)
        ico_base.save(ico_path, "ICO", sizes=[(s, s) for s in _ICO_SIZES])
        generated["ico"] = ico_path

        # ICNS — macOS icon bundle
        icns_path = output_dir / "icon.icns"
        icns_img = img.resize((_ICNS_SIZE, _ICNS_SIZE), Image.LANCZOS)
        icns_img.save(icns_path, "ICNS")
        generated["icns"] = icns_path

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate app icons (PNG, ICO, ICNS) from a source image.",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Source image path (PNG, JPG, WebP, etc. — min 256×256, ideally 1024×1024)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets/app_icon"),
        help="Output directory (default: assets/app_icon)",
    )
    args = parser.parse_args()

    try:
        generated = generate_icons(args.source, args.output_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for fmt, path in generated.items():
        print(f"  {fmt.upper():5s} → {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
