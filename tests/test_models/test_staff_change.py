"""Tests for StaffChangeRecord model."""

from datetime import date

import pytest

from timetable_generator.models.staff_change import StaffChangeRecord


def test_onboard_record():
    r = StaffChangeRecord(
        person_id="u1",
        date=date(2026, 1, 1),
        type="onboard",
        job_type="研发人员",
        business_line=None,
    )
    assert r.person_id == "u1"
    assert r.type == "onboard"
    assert r.job_type == "研发人员"
    assert r.business_line is None


def test_leave_record():
    r = StaffChangeRecord(
        person_id="u1",
        date=date(2026, 6, 30),
        type="leave",
        job_type=None,
        business_line=None,
    )
    assert r.type == "leave"
    assert r.job_type is None


def test_transfer_record():
    r = StaffChangeRecord(
        person_id="u1",
        date=date(2026, 3, 1),
        type="transfer",
        job_type=None,
        business_line="风控",
    )
    assert r.type == "transfer"
    assert r.business_line == "风控"


def test_invalid_type_raises():
    with pytest.raises(ValueError, match="type"):
        StaffChangeRecord(
            person_id="u1", date=date(2026, 1, 1), type="promote",
            job_type="研发人员", business_line=None,
        )


def test_onboard_without_job_type_raises():
    with pytest.raises(ValueError, match="job_type"):
        StaffChangeRecord(
            person_id="u1", date=date(2026, 1, 1), type="onboard",
            job_type=None, business_line=None,
        )


def test_empty_person_id_raises():
    with pytest.raises(ValueError, match="person_id"):
        StaffChangeRecord(
            person_id="", date=date(2026, 1, 1), type="onboard",
            job_type="研发人员", business_line=None,
        )
