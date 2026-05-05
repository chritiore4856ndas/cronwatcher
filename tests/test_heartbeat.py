"""Tests for HeartbeatMonitor."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.heartbeat import HeartbeatMonitor
from cronwatcher.alert_manager import AlertManager
from cronwatcher.job_tracker import JobTracker


NOW = datetime(2024, 6, 1, 12, 0, 0)
THRESHOLD = timedelta(minutes=30)


@pytest.fixture()
def tracker():
    return JobTracker()


@pytest.fixture()
def alert_manager():
    mgr = AlertManager()
    mgr._handler = MagicMock()
    mgr.register_handler(mgr._handler)
    return mgr


@pytest.fixture()
def monitor(tracker, alert_manager):
    return HeartbeatMonitor(
        tracker=tracker,
        alert_manager=alert_manager,
        zombie_threshold=THRESHOLD,
    )


def test_no_alert_for_finished_job(tracker, monitor, alert_manager):
    tracker.start("backup", started_at=NOW - timedelta(hours=2))
    tracker.finish("backup", finished_at=NOW - timedelta(hours=1))
    monitor.check(now=NOW)
    alert_manager._handler.assert_not_called()


def test_no_alert_within_threshold(tracker, monitor, alert_manager):
    tracker.start("backup", started_at=NOW - timedelta(minutes=10))
    monitor.check(now=NOW)
    alert_manager._handler.assert_not_called()


def test_zombie_alert_when_over_threshold(tracker, monitor, alert_manager):
    tracker.start("backup", started_at=NOW - timedelta(minutes=45))
    monitor.check(now=NOW)
    alert_manager._handler.assert_called_once()
    alert = alert_manager._handler.call_args[0][0]
    assert alert.kind == "zombie"
    assert "backup" in alert.job_name


def test_zombie_alert_sent_only_once(tracker, monitor, alert_manager):
    tracker.start("backup", started_at=NOW - timedelta(minutes=45))
    monitor.check(now=NOW)
    monitor.check(now=NOW + timedelta(minutes=5))
    assert alert_manager._handler.call_count == 1


def test_reset_alerts_allows_re_alert(tracker, monitor, alert_manager):
    tracker.start("backup", started_at=NOW - timedelta(minutes=45))
    monitor.check(now=NOW)
    monitor.reset_alerts()
    monitor.check(now=NOW + timedelta(minutes=5))
    assert alert_manager._handler.call_count == 2


def test_finished_job_clears_alerted_state(tracker, monitor):
    tracker.start("backup", started_at=NOW - timedelta(minutes=45))
    monitor.check(now=NOW)
    assert "backup" in monitor._alerted
    tracker.finish("backup", finished_at=NOW)
    monitor.check(now=NOW + timedelta(seconds=1))
    assert "backup" not in monitor._alerted
