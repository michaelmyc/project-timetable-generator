"""Tests for WorkHourRecord model."""

from datetime import date

import pytest

from timetable_generator.models.work_hour import WorkHourRecord


def test_work_hour_record():
    r = WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 1, 15), hours=8)
    assert r.project_id == "p1"
    assert r.person_id == "u1"
    assert r.hours == 8


def test_hours_zero_allowed():
    r = WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 1, 15), hours=0)
    assert r.hours == 0


def test_hours_exceed_8_raises():
    with pytest.raises(ValueError, match="hours"):
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 1, 15), hours=9)


def test_hours_negative_raises():
    with pytest.raises(ValueError, match="hours"):
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 1, 15), hours=-1)


def test_hours_non_integer_raises():
    with pytest.raises(ValueError, match="hours"):
        WorkHourRecord(project_id="p1", person_id="u1", date=date(2026, 1, 15), hours=4.5)


def test_empty_project_id_raises():
    with pytest.raises(ValueError, match="project_id"):
        WorkHourRecord(project_id="", person_id="u1", date=date(2026, 1, 15), hours=8)


def test_empty_person_id_raises():
    with pytest.raises(ValueError, match="person_id"):
        WorkHourRecord(project_id="p1", person_id="", date=date(2026, 1, 15), hours=8)
