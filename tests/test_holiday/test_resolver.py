"""Tests for HolidayResolver — workday判定 + 降级模式."""

from datetime import date

from timetable_generator.holiday.resolver import HolidayResolver


def test_fallback_weekend_only_saturday():
    resolver = HolidayResolver(holidays=None)
    assert resolver.is_workday(date(2026, 3, 7)) is False  # 周六


def test_fallback_weekend_only_sunday():
    resolver = HolidayResolver(holidays=None)
    assert resolver.is_workday(date(2026, 3, 8)) is False  # 周日


def test_fallback_weekday_monday():
    resolver = HolidayResolver(holidays=None)
    assert resolver.is_workday(date(2026, 3, 9)) is True  # 周一


def test_fallback_weekday_friday():
    resolver = HolidayResolver(holidays=None)
    assert resolver.is_workday(date(2026, 3, 13)) is True  # 周五


def test_with_holidays_holiday_not_workday():
    holidays = {"2026-01-01": {"name": "元旦", "is_workday": False}}
    resolver = HolidayResolver(holidays=holidays)
    assert resolver.is_workday(date(2026, 1, 1)) is False


def test_with_holidays_normal_weekday():
    holidays = {"2026-01-01": {"name": "元旦", "is_workday": False}}
    resolver = HolidayResolver(holidays=holidays)
    # 2026-01-02 is Friday → workday (not in holidays dict → weekday logic)
    assert resolver.is_workday(date(2026, 1, 2)) is True


def test_with_holidays_adjusted_workday():
    holidays = {"2026-02-07": {"name": "春节调休", "is_workday": True}}
    resolver = HolidayResolver(holidays=holidays)
    assert resolver.is_workday(date(2026, 2, 7)) is True  # 周六但调休→工作日


def test_is_fallback_mode():
    resolver = HolidayResolver(holidays=None)
    assert resolver.is_fallback is True


def test_not_fallback_mode_with_holidays():
    resolver = HolidayResolver(holidays={"2026-01-01": {"name": "元旦", "is_workday": False}})
    assert resolver.is_fallback is False
