"""Tests for flexible date parsing — multiple common formats."""

from datetime import date, datetime

import pytest

from timetable_generator.io.date_utils import parse_date_flexible


def test_parse_iso():
    assert parse_date_flexible("2026-03-02") == date(2026, 3, 2)


def test_parse_iso_padded():
    assert parse_date_flexible("2026-12-31") == date(2026, 12, 31)


def test_parse_slash_ymd():
    assert parse_date_flexible("2026/3/2") == date(2026, 3, 2)


def test_parse_slash_padded():
    assert parse_date_flexible("2026/03/02") == date(2026, 3, 2)


def test_parse_dot():
    assert parse_date_flexible("2026.3.2") == date(2026, 3, 2)


def test_parse_chinese():
    assert parse_date_flexible("2026年3月2日") == date(2026, 3, 2)


def test_parse_compact():
    assert parse_date_flexible("20260302") == date(2026, 3, 2)


def test_parse_us_slash():
    assert parse_date_flexible("3/2/2026") == date(2026, 3, 2)


def test_parse_none():
    assert parse_date_flexible(None) is None


def test_parse_blank():
    assert parse_date_flexible("") is None


def test_parse_whitespace():
    assert parse_date_flexible("  ") is None


def test_parse_date_object():
    d = date(2026, 3, 2)
    assert parse_date_flexible(d) == d


def test_parse_datetime_object():
    dt = datetime(2026, 3, 2, 14, 30)
    assert parse_date_flexible(dt) == date(2026, 3, 2)


def test_parse_iso_with_time():
    assert parse_date_flexible("2026-03-02T00:00:00") == date(2026, 3, 2)


def test_parse_invalid_raises():
    with pytest.raises(ValueError, match="无法解析日期"):
        parse_date_flexible("not a date")


def test_parse_garbage_raises():
    with pytest.raises(ValueError):
        parse_date_flexible("2026-13-45")


def test_parse_strips_whitespace():
    assert parse_date_flexible("  2026-03-02  ") == date(2026, 3, 2)
