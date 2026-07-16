"""HolidayApiClient — fetches holiday data from timor.tech API with retry."""

from __future__ import annotations

import httpx

API_BASE = "http://timor.tech/api/holiday/year"


class HolidayApiClient:
    """Async client for timor.tech holiday API.

    Retries up to max_retries times on failure.
    Returns None when all retries fail (degradation signal, ADR-0014).

    timor.tech returns keys in "MM-DD" format; we normalize to "YYYY-MM-DD".
    """

    def __init__(self, max_retries: int = 3, timeout: float = 10.0) -> None:
        self._max_retries = max_retries
        self._timeout = timeout

    async def fetch_year(self, year: int) -> dict[str, dict] | None:
        """Fetch holiday data for a given year.

        Returns parsed holiday dict with YYYY-MM-DD keys on success, None after all retries fail.
        """
        url = f"{API_BASE}/{year}"
        for _attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        raw = data.get("holiday", data)
                        # Normalize keys from "MM-DD" to "YYYY-MM-DD"
                        return {f"{year}-{k}": v for k, v in raw.items()}
            except httpx.HTTPError, httpx.InvalidURL:
                continue
        return None
