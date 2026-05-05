"""Tests for NotificationThrottle."""

from datetime import datetime, timedelta
import pytest

from cronwatcher.notification_throttle import NotificationThrottle


@pytest.fixture
def throttle():
    return NotificationThrottle(cooldown_seconds=60)


def _t(offset_seconds: int = 0) -> datetime:
    base = datetime(2024, 1, 1, 12, 0, 0)
    return base + timedelta(seconds=offset_seconds)


def test_first_alert_always_sent(throttle):
    assert throttle.should_send("backup", "missed", now=_t(0)) is True


def test_second_alert_within_cooldown_suppressed(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    assert throttle.should_send("backup", "missed", now=_t(30)) is False


def test_alert_allowed_after_cooldown_expires(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    assert throttle.should_send("backup", "missed", now=_t(61)) is True


def test_suppressed_count_increments(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    throttle.should_send("backup", "missed", now=_t(10))
    throttle.should_send("backup", "missed", now=_t(20))
    assert throttle.suppressed_count("backup", "missed") == 2


def test_suppressed_count_resets_after_cooldown(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    throttle.should_send("backup", "missed", now=_t(10))
    throttle.should_send("backup", "missed", now=_t(61))
    assert throttle.suppressed_count("backup", "missed") == 0


def test_different_kinds_tracked_independently(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    assert throttle.should_send("backup", "overdue", now=_t(5)) is True


def test_different_jobs_tracked_independently(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    assert throttle.should_send("cleanup", "missed", now=_t(5)) is True


def test_reset_clears_specific_job(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    throttle.reset("backup", "missed")
    assert throttle.should_send("backup", "missed", now=_t(10)) is True


def test_reset_all_clears_everything(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    throttle.should_send("cleanup", "overdue", now=_t(0))
    throttle.reset_all()
    assert throttle.should_send("backup", "missed", now=_t(10)) is True
    assert throttle.should_send("cleanup", "overdue", now=_t(10)) is True


def test_time_until_next_returns_none_before_first_send(throttle):
    assert throttle.time_until_next("backup", "missed", now=_t(0)) is None


def test_time_until_next_returns_remaining_seconds(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    remaining = throttle.time_until_next("backup", "missed", now=_t(20))
    assert remaining == pytest.approx(40.0)


def test_time_until_next_returns_none_after_cooldown(throttle):
    throttle.should_send("backup", "missed", now=_t(0))
    assert throttle.time_until_next("backup", "missed", now=_t(61)) is None
