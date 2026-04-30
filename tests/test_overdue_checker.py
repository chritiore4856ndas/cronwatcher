"""Tests for OverdueChecker."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call

import pytest

from cronwatcher.overdue_checker import OverdueChecker

UTC = timezone.utc


def _make_record(started_seconds_ago: float, running: bool = True):
    """Return a minimal fake JobRecord."""
    rec = MagicMock()
    dur = timedelta(seconds=started_seconds_ago) if running else None
    rec.duration.return_value = dur
    return rec


def _make_tracker(jobs: dict):
    tracker = MagicMock()
    tracker.running_jobs.return_value = jobs
    return tracker


@pytest.fixture()
def alert_manager():
    mgr = MagicMock()
    return mgr


def test_no_overdue_when_within_limit(alert_manager):
    tracker = _make_tracker({"backup": _make_record(30)})
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)
    checker.set_max_runtime("backup", 60)

    result = checker.check()

    assert result == []
    alert_manager.send.assert_not_called()


def test_overdue_job_triggers_alert(alert_manager):
    tracker = _make_tracker({"backup": _make_record(120)})
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)
    checker.set_max_runtime("backup", 60)

    result = checker.check()

    assert "backup" in result
    alert_manager.send.assert_called_once()
    kwargs = alert_manager.send.call_args.kwargs
    assert kwargs["kind"] == "overdue"
    assert kwargs["job_name"] == "backup"


def test_alert_sent_only_once_per_overdue_run(alert_manager):
    tracker = _make_tracker({"backup": _make_record(120)})
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)
    checker.set_max_runtime("backup", 60)

    checker.check()
    checker.check()

    assert alert_manager.send.call_count == 1


def test_reset_alerts_allows_re_alert(alert_manager):
    tracker = _make_tracker({"backup": _make_record(120)})
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)
    checker.set_max_runtime("backup", 60)

    checker.check()
    checker.reset_alerts("backup")
    checker.check()

    assert alert_manager.send.call_count == 2


def test_job_without_max_runtime_ignored(alert_manager):
    tracker = _make_tracker({"mystery": _make_record(9999)})
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)

    result = checker.check()

    assert result == []
    alert_manager.send.assert_not_called()


def test_set_max_runtime_rejects_non_positive(alert_manager):
    tracker = _make_tracker({})
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)

    with pytest.raises(ValueError):
        checker.set_max_runtime("job", 0)

    with pytest.raises(ValueError):
        checker.set_max_runtime("job", -5)


def test_reset_all_alerts(alert_manager):
    tracker = _make_tracker(
        {"a": _make_record(100), "b": _make_record(200)}
    )
    checker = OverdueChecker(tracker=tracker, alert_manager=alert_manager)
    checker.set_max_runtime("a", 50)
    checker.set_max_runtime("b", 50)

    checker.check()
    assert alert_manager.send.call_count == 2

    checker.reset_alerts()
    checker.check()
    assert alert_manager.send.call_count == 4
