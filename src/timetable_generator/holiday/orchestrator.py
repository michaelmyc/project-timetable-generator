"""HolidayOrchestrator — cache → API → fallback orchestration (ADR-0014)."""

from __future__ import annotations

from timetable_generator.holiday.api_client import HolidayApiClient
from timetable_generator.holiday.cache import HolidayCache
from timetable_generator.holiday.resolver import HolidayResolver


class HolidayOrchestrator:
    """Orchestrates holiday data retrieval: cache first, then API, then fallback.

    Flow (ADR-0014):
    1. Check cache for each year — cache hit skips API.
    2. For uncached years, call API (with retry).
    3. API success → cache result + use holiday data.
    4. API failure (all retries) → fallback to weekend-only mode.
    """

    def __init__(
        self,
        cache: HolidayCache,
        api_client: HolidayApiClient | None = None,
    ) -> None:
        self._cache = cache
        self._api_client = api_client or HolidayApiClient()

    async def ensure_year(self, year: int) -> HolidayResolver:
        """Ensure holiday data for a single year, return a resolver."""
        holidays = self._cache.load_year(year)
        if holidays is None:
            holidays = await self._api_client.fetch_year(year)
            if holidays is not None:
                self._cache.save_year(year, holidays)
        return HolidayResolver(holidays=holidays)

    async def ensure_years(self, *years: int) -> HolidayResolver:
        """Ensure holiday data for multiple years, merge into one resolver.

        If any year fails to fetch, falls back to weekend-only for all.
        """
        merged: dict[str, dict] = {}
        for year in years:
            data = self._cache.load_year(year)
            if data is None:
                data = await self._api_client.fetch_year(year)
                if data is not None:
                    self._cache.save_year(year, data)
            if data is None:
                # API failed for this year → fallback mode
                return HolidayResolver(holidays=None)
            merged.update(data)
        return HolidayResolver(holidays=merged)
