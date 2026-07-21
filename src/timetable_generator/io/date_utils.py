"""Flexible date parsing — supports multiple common date formats.

Used by CSV/Excel import, JSON param import, and UI date inputs so users can
enter dates in ISO, slash, dot, Chinese, compact, or US formats without errors.
"""

from __future__ import annotations

import re
from datetime import date, datetime

# Patterns ordered by specificity (unambiguous first). Each extracts (year, month, day).
_PATTERNS: list[tuple[re.Pattern[str], type]] = [
    # ISO: 2026-03-02
    (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), "ymd"),
    # Slash YYYY/M/D: 2026/3/2
    (re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$"), "ymd"),
    # Dot YYYY.M.D: 2026.3.2
    (re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$"), "ymd"),
    # Chinese: 2026年3月2日
    (re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$"), "ymd"),
    # Compact: 20260302
    (re.compile(r"^(\d{4})(\d{2})(\d{2})$"), "ymd"),
    # US: M/D/YYYY (month/day/year)
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$"), "mdy"),
]

_SUPPORTED = "YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, YYYY年M月D日, YYYYMMDD, M/D/YYYY"


def parse_date_flexible(value: str | date | datetime | None) -> date | None:
    """Parse a date from multiple common formats.

    Returns None for blank/None input. Raises ValueError if the string cannot
    be parsed in any supported format.

    Supported formats:
    - ISO:       2026-03-02
    - Slash:     2026/3/2  or  3/2/2026 (US month/day/year)
    - Dot:       2026.3.2
    - Chinese:   2026年3月2日
    - Compact:   20260302
    """
    if value is None:
        return None
    # Already a date/datetime object (e.g. from openpyxl cell) — use directly.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    for pattern, kind in _PATTERNS:
        m = pattern.match(s)
        if m:
            try:
                if kind == "ymd":
                    return date(int(m[1]), int(m[2]), int(m[3]))
                elif kind == "mdy":
                    return date(int(m[3]), int(m[1]), int(m[2]))
            except ValueError:
                continue
    # Last resort: try fromisoformat (handles e.g. 2026-03-02T00:00:00)
    try:
        return date.fromisoformat(s[:10] if "T" in s else s)
    except ValueError:
        raise ValueError(f"无法解析日期: '{s}'，支持格式: {_SUPPORTED}") from None
