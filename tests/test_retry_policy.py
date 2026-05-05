"""Tests for RetryPolicy."""
import pytest
from unittest.mock import MagicMock
from cronwatcher.retry_tracker import RetryTracker
from cronwatcher.retry_policy import RetryPolicy
from cronwatcher.alert_manager import AlertManager


@pytest.fixture
def alert_manager():
    mgr = AlertManager()
    mgr._handlers = []
    return mgr


@pytest.fixture
def policy(alert_manager):
    tracker = RetryTracker(max_retries=3)
    return RetryPolicy(tracker=tracker, alert_manager=alert_manager, max_retries=3)


def test_should_retry_true_initially(policy):
    assert policy.should_retry("backup") is True


def test_attempt_returns_true_below_limit(policy):
    result = policy.attempt("backup")
    assert result is True


def test_attempt_returns_false_when_exhausted(policy):
    for _ in range(2):
        policy.attempt("backup")
    result = policy.attempt("backup")
    assert result is False


def test_exhausted_sends_alert(policy, alert_manager):
    handler = MagicMock()
    alert_manager.register_handler(handler)
    for _ in range(3):
        policy.attempt("backup")
    handler.assert_called_once()
    alert = handler.call_args[0][0]
    assert alert.kind == "retries_exhausted"
    assert alert.job_name == "backup"


def test_no_alert_if_notify_disabled(alert_manager):
    tracker = RetryTracker(max_retries=2)
    pol = RetryPolicy(
        tracker=tracker,
        alert_manager=alert_manager,
        max_retries=2,
        notify_on_exhausted=False,
    )
    handler = MagicMock()
    alert_manager.register_handler(handler)
    pol.attempt("backup")
    pol.attempt("backup")
    handler.assert_not_called()


def test_success_resets_record(policy):
    policy.attempt("backup")
    policy.success("backup")
    assert policy.attempts_for("backup") == 0


def test_attempts_for_unknown_job_returns_zero(policy):
    assert policy.attempts_for("ghost") == 0
