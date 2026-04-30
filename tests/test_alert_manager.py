"""Tests for cronwatcher.alert_manager."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert, AlertManager


@pytest.fixture()
def manager() -> AlertManager:
    return AlertManager()


def test_alert_str_contains_kind_and_job():
    alert = Alert(job_name="backup", kind="missed", message="never started")
    text = str(alert)
    assert "MISSED" in text
    assert "backup" in text
    assert "never started" in text


def test_send_dispatches_to_handler(manager):
    handler = MagicMock()
    manager.register_handler(handler)
    alert = Alert(job_name="sync", kind="overdue", message="too slow")
    manager.send(alert)
    handler.assert_called_once_with(alert)


def test_send_stores_in_history(manager):
    alert = Alert(job_name="sync", kind="overdue", message="too slow")
    manager.send(alert)
    assert alert in manager.history


def test_multiple_handlers_all_called(manager):
    h1, h2 = MagicMock(), MagicMock()
    manager.register_handler(h1)
    manager.register_handler(h2)
    alert = Alert(job_name="job", kind="missed", message="x")
    manager.send(alert)
    h1.assert_called_once()
    h2.assert_called_once()


def test_faulty_handler_does_not_stop_others(manager):
    bad = MagicMock(side_effect=RuntimeError("boom"))
    good = MagicMock()
    manager.register_handler(bad)
    manager.register_handler(good)
    manager.send(Alert(job_name="job", kind="missed", message="x"))
    good.assert_called_once()


def test_alert_missed_sets_correct_kind(manager):
    alert = manager.alert_missed("backup", datetime(2024, 1, 1, 3, 0, 0))
    assert alert.kind == "missed"
    assert alert.job_name == "backup"
    assert "03:00:00" in alert.message


def test_alert_overdue_sets_correct_kind(manager):
    alert = manager.alert_overdue("etl", running_seconds=320.5, limit_seconds=300.0)
    assert alert.kind == "overdue"
    assert "320.5" in alert.message
    assert "300.0" in alert.message


def test_alert_recovered_sets_correct_kind(manager):
    alert = manager.alert_recovered("etl", duration_seconds=295.3)
    assert alert.kind == "recovered"
    assert "295.3" in alert.message


def test_history_for_filters_by_job(manager):
    manager.alert_missed("job_a", datetime.utcnow())
    manager.alert_overdue("job_b", 10, 5)
    manager.alert_missed("job_a", datetime.utcnow())
    assert len(manager.history_for("job_a")) == 2
    assert len(manager.history_for("job_b")) == 1


def test_clear_history(manager):
    manager.alert_missed("job", datetime.utcnow())
    manager.clear_history()
    assert manager.history == []
