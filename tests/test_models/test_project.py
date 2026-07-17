"""Tests for Project model."""

from datetime import date

import pytest

from timetable_generator.models.project import Project


def test_project_creation_with_required_fields():
    p = Project(
        id="p1",
        name="支付系统",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        target_ratio=0.3,
        required_job_types=["研发人员"],
        associated_person_ids=["u1"],
    )
    assert p.id == "p1"
    assert p.name == "支付系统"
    assert p.target_ratio == 0.3
    assert p.required_job_types == ["研发人员"]
    assert p.associated_person_ids == ["u1"]


def test_project_invalid_ratio_above_1_raises():
    with pytest.raises(ValueError, match="target_ratio"):
        Project(
            id="p1", name="A", start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            target_ratio=1.5, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )


def test_project_invalid_ratio_negative_raises():
    with pytest.raises(ValueError, match="target_ratio"):
        Project(
            id="p1", name="A", start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            target_ratio=-0.1, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )


def test_project_empty_job_types_allowed():
    """required_job_types may be empty — means no job type constraint."""
    p = Project(
        id="p1", name="A", start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
        target_ratio=0.3, required_job_types=[], associated_person_ids=["u1"],
    )
    assert p.required_job_types == []


def test_project_end_before_start_raises():
    with pytest.raises(ValueError, match="date"):
        Project(
            id="p1", name="A", start_date=date(2026, 3, 31), end_date=date(2026, 1, 1),
            target_ratio=0.3, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )


def test_project_empty_id_raises():
    with pytest.raises(ValueError, match="id"):
        Project(
            id="", name="A", start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            target_ratio=0.3, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )


def test_project_empty_associated_persons_raises():
    with pytest.raises(ValueError, match="associated_person"):
        Project(
            id="p1", name="A", start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            target_ratio=0.3, required_job_types=["研发人员"], associated_person_ids=[],
        )
