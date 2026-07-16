"""Tests for UI session state."""

from datetime import date

from timetable_generator.ui.session import SessionState


def test_session_starts_empty():
    s = SessionState()
    assert s.global_span is None
    assert s.staff == []
    assert s.projects == []
    assert s.generation_result is None
    assert not s.can_generate


def test_set_global_span():
    s = SessionState()
    s.set_span(date(2026, 1, 1), date(2026, 6, 30))
    assert s.global_span is not None
    assert s.global_span.start_date == date(2026, 1, 1)


def test_add_staff():
    s = SessionState()
    s.add_staff("张三")
    assert len(s.staff) == 1
    assert s.staff[0].name == "张三"
    assert s.staff[0].job_type == "研发人员"


def test_add_project():
    from timetable_generator.models.project import Project
    s = SessionState()
    s.set_span(date(2026, 1, 1), date(2026, 6, 30))
    p = Project("p1", "A", date(2026, 1, 1), date(2026, 6, 30),
                0.3, ["研发人员"], ["张三"])
    s.add_project(p)
    assert len(s.projects) == 1


def test_can_generate():
    s = SessionState()
    assert not s.can_generate
    s.set_span(date(2026, 1, 1), date(2026, 6, 30))
    assert not s.can_generate
    s.add_staff("张三")
    assert not s.can_generate
    from timetable_generator.models.project import Project
    s.add_project(Project("p1", "A", date(2026, 1, 1), date(2026, 6, 30),
                          0.3, ["研发人员"], ["张三"]))
    assert s.can_generate


def test_get_staff_ids():
    s = SessionState()
    s.add_staff("张三")
    s.add_staff("李四")
    assert s.get_staff_ids() == ["张三", "李四"]


def test_clear_result():
    s = SessionState()
    s.generation_result = "fake"
    s.clear_result()
    assert s.generation_result is None
