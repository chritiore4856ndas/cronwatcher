"""Tests for WindowEntry and WindowRegistry."""
from datetime import datetime, time

import pytest

from cronwatcher.job_window import WindowEntry, WindowRegistry


@pytest.fixture()
def registry() -> WindowRegistry:
    return WindowRegistry()


# --- WindowEntry.is_active ---

def test_is_active_within_window():
    entry = WindowEntry(start=time(9, 0), end=time(17, 0))
    at = datetime(2024, 6, 3, 12, 0)  # Monday noon
    assert entry.is_active(at) is True


def test_is_inactive_before_window():
    entry = WindowEntry(start=time(9, 0), end=time(17, 0))
    at = datetime(2024, 6, 3, 7, 30)  # Monday 07:30
    assert entry.is_active(at) is False


def test_is_inactive_after_window():
    entry = WindowEntry(start=time(9, 0), end=time(17, 0))
    at = datetime(2024, 6, 3, 18, 0)  # Monday 18:00
    assert entry.is_active(at) is False


def test_is_inactive_on_excluded_day():
    entry = WindowEntry(start=time(9, 0), end=time(17, 0), days=(0, 1, 2, 3, 4))  # Mon-Fri
    at = datetime(2024, 6, 8, 12, 0)  # Saturday
    assert entry.is_active(at) is False


def test_overnight_window_active_before_midnight():
    entry = WindowEntry(start=time(22, 0), end=time(6, 0))
    at = datetime(2024, 6, 3, 23, 0)
    assert entry.is_active(at) is True


def test_overnight_window_active_after_midnight():
    entry = WindowEntry(start=time(22, 0), end=time(6, 0))
    at = datetime(2024, 6, 3, 2, 0)
    assert entry.is_active(at) is True


def test_to_dict_contains_expected_keys():
    entry = WindowEntry(start=time(8, 0), end=time(20, 0), days=(0, 1, 2, 3, 4))
    d = entry.to_dict()
    assert d["start"] == "08:00"
    assert d["end"] == "20:00"
    assert d["days"] == [0, 1, 2, 3, 4]


# --- WindowRegistry ---

def test_get_window_unknown_job_returns_none(registry):
    assert registry.get_window("backup") is None


def test_set_and_get_window(registry):
    registry.set_window("backup", time(1, 0), time(5, 0))
    entry = registry.get_window("backup")
    assert entry is not None
    assert entry.start == time(1, 0)


def test_is_within_window_no_restriction_returns_true(registry):
    assert registry.is_within_window("norestriction") is True


def test_is_within_window_inside(registry):
    registry.set_window("job", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 10, 0)  # Monday inside window
    assert registry.is_within_window("job", at) is True


def test_is_within_window_outside(registry):
    registry.set_window("job", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 20, 0)  # Monday outside window
    assert registry.is_within_window("job", at) is False


def test_remove_window(registry):
    registry.set_window("job", time(8, 0), time(18, 0))
    removed = registry.remove_window("job")
    assert removed is True
    assert registry.get_window("job") is None


def test_remove_nonexistent_window_returns_false(registry):
    assert registry.remove_window("ghost") is False


def test_all_jobs_returns_registered(registry):
    registry.set_window("a", time(8, 0), time(16, 0))
    registry.set_window("b", time(9, 0), time(17, 0))
    assert set(registry.all_jobs().keys()) == {"a", "b"}
