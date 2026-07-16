"""Tests for HolidayCache."""


from timetable_generator.holiday.cache import HolidayCache


def test_cache_save_and_load(tmp_path):
    cache = HolidayCache(cache_dir=tmp_path)
    data = {"2026-01-01": {"name": "元旦", "is_workday": False}}
    cache.save_year(2026, data)
    loaded = cache.load_year(2026)
    assert loaded is not None
    assert loaded["2026-01-01"]["name"] == "元旦"
    assert loaded["2026-01-01"]["is_workday"] is False


def test_cache_miss_returns_none(tmp_path):
    cache = HolidayCache(cache_dir=tmp_path)
    assert cache.load_year(2025) is None


def test_cache_overwrite_on_save(tmp_path):
    cache = HolidayCache(cache_dir=tmp_path)
    cache.save_year(2026, {"2026-01-01": {"name": "元旦", "is_workday": False}})
    cache.save_year(2026, {"2026-01-01": {"name": "New Year", "is_workday": False}})
    loaded = cache.load_year(2026)
    assert loaded["2026-01-01"]["name"] == "New Year"


def test_cache_file_path_per_year(tmp_path):
    cache = HolidayCache(cache_dir=tmp_path)
    cache.save_year(2026, {})
    cache.save_year(2025, {})
    # Two separate files
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 2
