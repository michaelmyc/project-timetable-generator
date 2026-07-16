"""Tests for GlobalSpan and StaffState (default fallback + change-driven derivation)."""

from datetime import date

from timetable_generator.models.staff_change import StaffChangeRecord
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_default_fallback_active_span():
    span = GlobalSpan(start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
    state = StaffState.from_changes(person_id="u1", changes=[], global_span=span)
    assert state.active_span == (date(2026, 1, 1), date(2026, 6, 30))
    assert state.job_type == "研发人员"
    assert state.business_line is None


def test_with_onboard_leave():
    span = GlobalSpan(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    changes = [
        StaffChangeRecord("u1", date(2026, 2, 1), "onboard", "测试", "支付"),
        StaffChangeRecord("u1", date(2026, 5, 1), "leave"),
    ]
    state = StaffState.from_changes("u1", changes, span)
    assert state.active_span == (date(2026, 2, 1), date(2026, 5, 1))
    assert state.job_type == "测试"
    assert state.business_line == "支付"


def test_onboard_without_leave_active_until_span_end():
    span = GlobalSpan(start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
    changes = [
        StaffChangeRecord("u1", date(2026, 3, 1), "onboard", "研发人员", None),
    ]
    state = StaffState.from_changes("u1", changes, span)
    assert state.active_span == (date(2026, 3, 1), date(2026, 6, 30))


def test_transfer_changes_business_line():
    span = GlobalSpan(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    changes = [
        StaffChangeRecord("u1", date(2026, 1, 1), "onboard", "研发人员", "支付"),
        StaffChangeRecord("u1", date(2026, 6, 1), "transfer", business_line="风控"),
    ]
    state = StaffState.from_changes("u1", changes, span)
    # Current business_line at end of span should be 风控
    assert state.business_line_at(date(2026, 5, 15)) == "支付"
    assert state.business_line_at(date(2026, 7, 1)) == "风控"


def test_is_active_on_date():
    span = GlobalSpan(start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
    changes = [
        StaffChangeRecord("u1", date(2026, 2, 1), "onboard", "研发人员", None),
        StaffChangeRecord("u1", date(2026, 5, 1), "leave"),
    ]
    state = StaffState.from_changes("u1", changes, span)
    assert not state.is_active_on(date(2026, 1, 15))  # before onboard
    assert state.is_active_on(date(2026, 2, 1))  # onboard date
    assert state.is_active_on(date(2026, 4, 30))  # before leave
    assert not state.is_active_on(date(2026, 5, 1))  # leave date
    assert not state.is_active_on(date(2026, 6, 15))  # after leave


def test_default_fallback_is_active_on_any_date_in_span():
    span = GlobalSpan(start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
    state = StaffState.from_changes("u1", [], span)
    assert state.is_active_on(date(2026, 1, 1))
    assert state.is_active_on(date(2026, 6, 30))
    assert state.is_active_on(date(2026, 3, 15))
    assert not state.is_active_on(date(2025, 12, 31))
    assert not state.is_active_on(date(2026, 7, 1))
