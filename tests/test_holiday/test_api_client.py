"""Tests for HolidayApiClient."""

import httpx
import pytest

from timetable_generator.holiday.api_client import HolidayApiClient


@pytest.mark.asyncio
async def test_fetch_year_success(httpx_mock):
    httpx_mock.add_response(
        url="http://timor.tech/api/holiday/year/2026",
        json={"holiday": {"01-01": {"holiday": True, "name": "元旦"}}},
    )
    client = HolidayApiClient()
    result = await client.fetch_year(2026)
    assert result is not None
    assert "2026-01-01" in result


@pytest.mark.asyncio
async def test_fetch_year_retry_3_then_none(httpx_mock):
    httpx_mock.add_response(
        url="http://timor.tech/api/holiday/year/2026",
        status_code=500,
        is_reusable=True,
    )
    client = HolidayApiClient(max_retries=3)
    result = await client.fetch_year(2026)
    assert result is None  # All retries failed → degradation signal


@pytest.mark.asyncio
async def test_fetch_year_network_error_returns_none(httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("connection refused"),
        url="http://timor.tech/api/holiday/year/2026",
        is_reusable=True,
    )
    client = HolidayApiClient(max_retries=2)
    result = await client.fetch_year(2026)
    assert result is None
