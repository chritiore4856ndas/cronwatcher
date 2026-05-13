"""Tests for blackout period registry and alert filter."""
from __future__ import annotations

from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert
from cronwatcher.blackout_alert_filter import BlackoutAlertFilter
from cronwatcher.job_blackout import BlackoutPeriod, BlackoutRegistry


@pytest.fixture()
def registry() -> BlackoutRegistry:
    return BlackoutRegistry()


def _dt(hour: int, minute: int = 0, weekday: int = 0) -> datetime:
    """Return a datetime on a Monday (weekday=0) at the given time."""
    base = datetime(2024, 1, 1)  # Monday
    days_offset = weekday
    return base.replace(hour=hour, minute=minute, day=1 + days_offset)


# --- BlackoutPeriod ---

def test_period_active_within_window():
    p = BlackoutPeriod(start=time(2, 0), end=time(4, 0))
    assert p.is_active(_dt(3, 0))


def test_period_inactive_outside_window():
    p = BlackoutPeriod(start=time(2, 0), end=time(4, 0))
    assert not p.is_active(_dt(5, 0))


def test_overnight_period_active_after_start():
    p = BlackoutPeriod(start=time(23, 0), end=time(1, 0))
    assert p.is_active(_dt(23, 30))


def test_overnight_period_active_before_end():
    p = BlackoutPeriod(start=time(23, 0), end=time(1, 0))
    assert p.is_active(_dt(0, 30))


def test_period_respects_day_filter_active():
    p = BlackoutPeriod(start=time(2, 0), end=time(4, 0), days=[0])  # Monday only
    assert p.is_active(_dt(3, 0, weekday=0))


def test_period_respects_day_filter_inactive():
    p = BlackoutPeriod(start=time(2, 0), end=time(4, 0), days=[0])  # Monday only
    assert not p.is_active(_dt(3, 0, weekday=1))  # Tuesday


def test_period_to_dict():
    p = BlackoutPeriod(start=time(2, 0), end=time(4, 0), days=[0, 6])
    d = p.to_dict()
    assert d["start"] == "02:00"
    assert d["end"] == "04:00"
    assert d["days"] == [0, 6]


# --- BlackoutRegistry ---

def test_is_blacked_out_true(registry):
    registry.add("backup", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    assert registry.is_blacked_out("backup", _dt(2, 0))


def test_is_blacked_out_false(registry):
    registry.add("backup", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    assert not registry.is_blacked_out("backup", _dt(5, 0))


def test_unknown_job_not_blacked_out(registry):
    assert not registry.is_blacked_out("ghost", _dt(2, 0))


def test_remove_clears_periods(registry):
    registry.add("job", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    registry.remove("job")
    assert not registry.is_blacked_out("job", _dt(2, 0))


def test_export_all_returns_dicts(registry):
    registry.add("job", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    exported = registry.export_all()
    assert "job" in exported
    assert exported["job"][0]["start"] == "01:00"


# --- BlackoutAlertFilter ---

def _alert(job: str = "backup") -> Alert:
    return Alert(kind="missed", job_name=job, message="missed")


def test_filter_suppresses_during_blackout(registry):
    registry.add("backup", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    sink = MagicMock()
    f = BlackoutAlertFilter(registry)
    f.add_handler(sink)
    f(_alert("backup"), now=_dt(2, 0))
    sink.assert_not_called()
    assert f.suppressed_count == 1


def test_filter_forwards_outside_blackout(registry):
    registry.add("backup", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    sink = MagicMock()
    f = BlackoutAlertFilter(registry)
    f.add_handler(sink)
    f(_alert("backup"), now=_dt(5, 0))
    sink.assert_called_once()


def test_reset_suppressed(registry):
    registry.add("backup", BlackoutPeriod(start=time(1, 0), end=time(3, 0)))
    f = BlackoutAlertFilter(registry)
    f(_alert("backup"), now=_dt(2, 0))
    f.reset_suppressed()
    assert f.suppressed_count == 0
