"""Tests for StaffInfo model — including onboard/leave date fields."""

from datetime import date

import pytest

from timetable_generator.models.staff_info import DEFAULT_JOB_TYPE, StaffInfo


def test_staff_info_defaults():
    s = StaffInfo(name="张三")
    assert s.name == "张三"
    assert s.job_type == DEFAULT_JOB_TYPE
    assert s.business_line is None
    assert s.annual_leave_days == 0
    assert s.onboard_date is None
    assert s.leave_date is None
    assert s.id == "张三"


def test_staff_info_with_onboard_and_leave_dates():
    s = StaffInfo(
        name="张三",
        job_type="研发人员",
        business_line="平台",
        annual_leave_days=5,
        onboard_date=date(2025, 1, 1),
        leave_date=date(2026, 12, 31),
    )
    assert s.onboard_date == date(2025, 1, 1)
    assert s.leave_date == date(2026, 12, 31)


def test_staff_info_onboard_only():
    s = StaffInfo(name="张三", onboard_date=date(2025, 1, 1))
    assert s.onboard_date == date(2025, 1, 1)
    assert s.leave_date is None


def test_staff_info_leave_only():
    s = StaffInfo(name="张三", leave_date=date(2026, 12, 31))
    assert s.onboard_date is None
    assert s.leave_date == date(2026, 12, 31)


def test_staff_info_leave_before_onboard_raises():
    with pytest.raises(ValueError, match="leave_date"):
        StaffInfo(
            name="张三",
            onboard_date=date(2026, 12, 31),
            leave_date=date(2025, 1, 1),
        )


def test_staff_info_leave_equals_onboard_allowed():
    same = date(2026, 6, 1)
    s = StaffInfo(name="张三", onboard_date=same, leave_date=same)
    assert s.onboard_date == same
    assert s.leave_date == same


def test_staff_info_empty_name_raises():
    with pytest.raises(ValueError, match="name"):
        StaffInfo(name="")
