"""Integration tests: cache → API → fallback orchestration."""

from datetime import date

import pytest

from timetable_generator.holiday.api_client import HolidayApiClient
from timetable_generator.holiday.cache import HolidayCache
from timetable_generator.holiday.orchestrator import HolidayOrchestrator


@pytest.mark.asyncio
async def test_cache_hit_no_api_call(tmp_path, httpx_mock):
    cache = HolidayCache(cache_dir=tmp_path)
    cache.save_year(2026, {"2026-01-01": {"name": "元旦", "is_workday": False}})
    orch = HolidayOrchestrator(cache=cache, api_client=HolidayApiClient())
    resolver = await orch.ensure_year(2026)
    # API should not be called — cache hit
    assert not httpx_mock.get_requests()
    assert not resolver.is_fallback
    assert resolver.is_workday(date(2026, 1, 1)) is False


@pytest.mark.asyncio
async def test_api_success_caches_result(tmp_path, httpx_mock):
    httpx_mock.add_response(
        url="http://timor.tech/api/holiday/year/2026",
        json={"holiday": {"01-01": {"holiday": True, "name": "元旦", "wage": 3}}},
    )
    cache = HolidayCache(cache_dir=tmp_path)
    orch = HolidayOrchestrator(cache=cache, api_client=HolidayApiClient())
    resolver = await orch.ensure_year(2026)
    assert not resolver.is_fallback
    # Result should be cached
    cached = cache.load_year(2026)
    assert cached is not None
    assert "2026-01-01" in cached

@pytest.mark.asyncio
async def test_api_fail_fallback_weekend(tmp_path, httpx_mock):
    httpx_mock.add_response(
        url="http://timor.tech/api/holiday/year/2026",
        status_code=500,
        is_reusable=True,
    )
    cache = HolidayCache(cache_dir=tmp_path)
    orch = HolidayOrchestrator(cache=cache, api_client=HolidayApiClient(max_retries=3))
    resolver = await orch.ensure_year(2026)
    assert resolver.is_fallback
    # Weekend logic
    assert resolver.is_workday(date(2026, 3, 7)) is False  # Saturday
    assert resolver.is_workday(date(2026, 3, 9)) is True  # Monday


@pytest.mark.asyncio
async def test_ensure_multiple_years(tmp_path, httpx_mock):
    httpx_mock.add_response(
        url="http://timor.tech/api/holiday/year/2025",
        json={"holiday": {"01-01": {"holiday": True, "name": "元旦"}}},
    )
    httpx_mock.add_response(
        url="http://timor.tech/api/holiday/year/2026",
        json={"holiday": {"01-01": {"holiday": True, "name": "元旦"}}},
    )
    cache = HolidayCache(cache_dir=tmp_path)
    orch = HolidayOrchestrator(cache=cache, api_client=HolidayApiClient())
    resolver = await orch.ensure_years(2025, 2026)
    assert not resolver.is_fallback
    assert resolver.is_workday(date(2025, 1, 1)) is False
    assert resolver.is_workday(date(2026, 1, 1)) is False
