"""Unit tests for StaffState.from_info — MVP onboard/leave → active_span."""

from datetime import date

from timetable_generator.models.staff_info import StaffInfo
from timetable_generator.models.staff_state import GlobalSpan, StaffState


def test_from_info_no_dates_defaults_to_full_span():
    """No onboard/leave → active_span = global_span (inclusive both ends)."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1")
    state = StaffState.from_info(info, span)
    assert state.is_active_on(date(2026, 3, 2))
    assert state.is_active_on(date(2026, 3, 13))
    assert state._end_is_leave is False


def test_from_info_onboard_only():
    """Onboard date set, no leave → active from onboard to span end."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", onboard_date=date(2026, 3, 5))
    state = StaffState.from_info(info, span)
    assert not state.is_active_on(date(2026, 3, 4))
    assert state.is_active_on(date(2026, 3, 5))
    assert state.is_active_on(date(2026, 3, 13))


def test_from_info_leave_only():
    """Leave date set, no onboard → active from span start through leave (inclusive)."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", leave_date=date(2026, 3, 10))
    state = StaffState.from_info(info, span)
    assert state.is_active_on(date(2026, 3, 2))
    assert state.is_active_on(date(2026, 3, 10))  # leave_date = last active day (inclusive)
    assert not state.is_active_on(date(2026, 3, 11))
    assert state._end_is_leave is True


def test_from_info_both_dates():
    """Both onboard and leave → active on [onboard, leave] inclusive."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", onboard_date=date(2026, 3, 5), leave_date=date(2026, 3, 10))
    state = StaffState.from_info(info, span)
    assert not state.is_active_on(date(2026, 3, 4))
    assert state.is_active_on(date(2026, 3, 5))
    assert state.is_active_on(date(2026, 3, 10))
    assert not state.is_active_on(date(2026, 3, 11))


def test_from_info_clamp_onboard_before_span():
    """Onboard before span start → clamped to span start."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", onboard_date=date(2025, 1, 1))
    state = StaffState.from_info(info, span)
    assert state.is_active_on(date(2026, 3, 2))


def test_from_info_clamp_leave_after_span():
    """Leave after span end → clamped to span end, not treated as leave."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", leave_date=date(2027, 12, 31))
    state = StaffState.from_info(info, span)
    assert state.is_active_on(date(2026, 3, 13))
    assert state._end_is_leave is False  # clamped, not a real leave


def test_from_info_fully_outside_span_before():
    """Staff left before span starts → no active days in span."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", onboard_date=date(2025, 1, 1), leave_date=date(2025, 6, 1))
    state = StaffState.from_info(info, span)
    for d in [date(2026, 3, 2), date(2026, 3, 5), date(2026, 3, 13)]:
        assert not state.is_active_on(d)


def test_from_info_fully_outside_span_after():
    """Staff onboard after span ends → no active days in span."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", onboard_date=date(2026, 4, 1))
    state = StaffState.from_info(info, span)
    for d in [date(2026, 3, 2), date(2026, 3, 13)]:
        assert not state.is_active_on(d)


def test_from_info_onboard_equals_leave():
    """Onboard == leave → active only on that single day."""
    span = GlobalSpan(date(2026, 3, 2), date(2026, 3, 13))
    info = StaffInfo(name="u1", onboard_date=date(2026, 3, 5), leave_date=date(2026, 3, 5))
    state = StaffState.from_info(info, span)
    assert state.is_active_on(date(2026, 3, 5))
    assert not state.is_active_on(date(2026, 3, 4))
    assert not state.is_active_on(date(2026, 3, 6))
