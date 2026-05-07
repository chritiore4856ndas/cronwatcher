"""Tests for job_timeout module."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_timeout import JobTimeoutChecker, TimeoutRegistry
from cronwatcher.job_tracker import JobRecord, JobTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_running_record(job_name: str, elapsed_seconds: float) -> JobRecord:
    start = datetime.utcnow() - timedelta(seconds=elapsed_seconds)
    rec = MagicMock(spec=JobRecord)
    rec.job_name = job_name
    rec.is_running.return_value = True
    rec.duration.return_value = timedelta(seconds=elapsed_seconds)
    return rec


def _make_finished_record(job_name: str) -> JobRecord:
    rec = MagicMock(spec=JobRecord)
    rec.job_name = job_name
    rec.is_running.return_value = False
    rec.duration.return_value = timedelta(seconds=30)
    return rec


@pytest.fixture()
def registry() -> TimeoutRegistry:
    return TimeoutRegistry()


@pytest.fixture()
def alert_manager() -> AlertManager:
    am = AlertManager()
    am._handlers = []
    am._history = []
    return am


@pytest.fixture()
def tracker() -> MagicMock:
    return MagicMock(spec=JobTracker)


# ---------------------------------------------------------------------------
# TimeoutRegistry tests
# ---------------------------------------------------------------------------

def test_set_and_get_timeout(registry):
    registry.set_timeout("backup", 120)
    assert registry.get_timeout("backup") == timedelta(seconds=120)


def test_get_unknown_job_returns_none(registry):
    assert registry.get_timeout("nonexistent") is None


def test_negative_timeout_raises(registry):
    with pytest.raises(ValueError):
        registry.set_timeout("job", -5)


def test_zero_timeout_raises(registry):
    with pytest.raises(ValueError):
        registry.set_timeout("job", 0)


def test_remove_timeout(registry):
    registry.set_timeout("job", 60)
    registry.remove_timeout("job")
    assert registry.get_timeout("job") is None


def test_all_jobs_returns_copy(registry):
    registry.set_timeout("a", 10)
    registry.set_timeout("b", 20)
    result = registry.all_jobs()
    assert set(result.keys()) == {"a", "b"}
    result["c"] = timedelta(seconds=30)  # mutating copy should not affect registry
    assert registry.get_timeout("c") is None


# ---------------------------------------------------------------------------
# JobTimeoutChecker tests
# ---------------------------------------------------------------------------

def test_no_alert_within_timeout(registry, tracker, alert_manager):
    registry.set_timeout("sync", 60)
    tracker.get.return_value = _make_running_record("sync", 30)
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    assert alert_manager.history() == []


def test_alert_fires_when_timeout_exceeded(registry, tracker, alert_manager):
    registry.set_timeout("sync", 60)
    tracker.get.return_value = _make_running_record("sync", 90)
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    alerts = alert_manager.history()
    assert len(alerts) == 1
    assert alerts[0].kind == "timeout"
    assert alerts[0].job_name == "sync"


def test_alert_fires_only_once(registry, tracker, alert_manager):
    registry.set_timeout("sync", 60)
    tracker.get.return_value = _make_running_record("sync", 120)
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    checker.check()
    assert len(alert_manager.history()) == 1


def test_no_alert_for_finished_job(registry, tracker, alert_manager):
    registry.set_timeout("sync", 60)
    tracker.get.return_value = _make_finished_record("sync")
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    assert alert_manager.history() == []


def test_no_alert_when_job_not_tracked(registry, tracker, alert_manager):
    registry.set_timeout("sync", 60)
    tracker.get.return_value = None
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    assert alert_manager.history() == []


def test_reset_alerts_clears_flag(registry, tracker, alert_manager):
    registry.set_timeout("sync", 60)
    tracker.get.return_value = _make_running_record("sync", 120)
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    assert len(alert_manager.history()) == 1
    checker.reset_alerts("sync")
    checker.check()
    assert len(alert_manager.history()) == 2


def test_alert_message_contains_job_name(registry, tracker, alert_manager):
    registry.set_timeout("nightly", 30)
    tracker.get.return_value = _make_running_record("nightly", 90)
    checker = JobTimeoutChecker(registry, tracker, alert_manager)
    checker.check()
    msg = alert_manager.history()[0].message
    assert "nightly" in msg
    assert "30" in msg
