"""HolidayCache — local JSON cache for holiday data, organized by year."""

from __future__ import annotations

import json
from pathlib import Path


class HolidayCache:
    """Local file-based cache for holiday data, one JSON file per year.

    Cache is the only business-related data allowed to persist locally (ADR-0006 D3).
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def save_year(self, year: int, data: dict[str, dict]) -> None:
        """Save holiday data for a year to cache."""
        path = self._cache_dir / f"{year}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_year(self, year: int) -> dict[str, dict] | None:
        """Load holiday data for a year from cache. Returns None if not cached."""
        path = self._cache_dir / f"{year}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
