"""HolidayResolver — determines workday status, with weekend-only fallback (ADR-0014)."""

from __future__ import annotations

from datetime import date


class HolidayResolver:
    """Resolves whether a date is a workday, using holiday data or weekend-only fallback.

    With holiday data: dates in the holiday dict are classified by their is_workday flag.
    Dates not in the dict are classified by weekday (Mon-Fri = workday, Sat/Sun = not).

    Without holiday data (fallback mode): purely weekend-based (Mon-Fri = workday).
    """

    def __init__(self, holidays: dict[str, dict] | None) -> None:
        self._holidays = holidays
        self._fallback = holidays is None

    @property
    def is_fallback(self) -> bool:
        """True if operating in weekend-only fallback mode."""
        return self._fallback

    def is_workday(self, d: date) -> bool:
        """Check if a date is a workday.

        - Fallback mode: Mon-Fri = workday, Sat/Sun = not.
        - With holidays: check holiday dict first, then fall back to weekday logic.
        """
        if self._holidays is not None:
            key = d.strftime("%Y-%m-%d")
            if key in self._holidays:
                return self._holidays[key].get("is_workday", False)
        # No holiday entry: weekday logic
        return d.weekday() < 5  # 0=Mon ... 4=Fri, 5=Sat, 6=Sun
