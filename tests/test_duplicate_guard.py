"""Tests for cronwatcher.duplicate_guard."""
import pytest

from cronwatcher.alert_manager import AlertManager
from cronwatcher.duplicate_guard import DuplicateGuard


@pytest.fixture()
def alert_manager() -> AlertManager:
    mgr = AlertManager()
    mgr.register_handler(lambda a: None)  # no-op handler
    return mgr


@pytest.fixture()
def guard(alert_manager) -> DuplicateGuard:
    return DuplicateGuard(alert_manager=alert_manager)


def test_start_accepts_new_job(guard):
    assert guard.start("backup") is True


def test_start_rejects_duplicate(guard):
    guard.start("backup")
    assert guard.start("backup") is False


def test_duplicate_fires_alert(guard, alert_manager):
    guard.start("backup")
    guard.start("backup")
    alerts = alert_manager.history
    assert len(alerts) == 1
    assert alerts[0].kind == "duplicate"
    assert alerts[0].job_name == "backup"


def test_alert_message_contains_job_name(guard, alert_manager):
    guard.start("sync")
    guard.start("sync")
    assert "sync" in alert_manager.history[0].message


def test_finish_releases_lock(guard):
    guard.start("backup")
    guard.finish("backup")
    assert guard.is_running("backup") is False


def test_finish_returns_true_if_was_running(guard):
    guard.start("backup")
    assert guard.finish("backup") is True


def test_finish_returns_false_if_not_running(guard):
    assert guard.finish("backup") is False


def test_restart_after_finish_is_accepted(guard):
    guard.start("backup")
    guard.finish("backup")
    assert guard.start("backup") is True


def test_is_running_true_while_locked(guard):
    guard.start("backup")
    assert guard.is_running("backup") is True


def test_is_running_false_before_start(guard):
    assert guard.is_running("backup") is False


def test_independent_jobs_dont_interfere(guard):
    guard.start("job_a")
    assert guard.start("job_b") is True


def test_reset_clears_all_locks(guard):
    guard.start("job_a")
    guard.start("job_b")
    guard.reset()
    assert guard.is_running("job_a") is False
    assert guard.is_running("job_b") is False


def test_multiple_duplicates_fire_multiple_alerts(guard, alert_manager):
    guard.start("backup")
    guard.start("backup")
    guard.start("backup")
    assert len(alert_manager.history) == 2
