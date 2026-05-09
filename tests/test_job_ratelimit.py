"""Tests for RateLimitRegistry and RateLimitEntry."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.job_ratelimit import RateLimitEntry, RateLimitRegistry
from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.ratelimit_alert_filter import RateLimitAlertFilter


T0 = datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture
def registry() -> RateLimitRegistry:
    return RateLimitRegistry()


# --- RateLimitEntry ---

def test_entry_allowed_when_no_last_run():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60)
    assert entry.is_allowed() is True


def test_entry_blocked_within_interval():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60, last_run=T0)
    now = T0 + timedelta(seconds=30)
    assert entry.is_allowed(now) is False


def test_entry_allowed_after_interval():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60, last_run=T0)
    now = T0 + timedelta(seconds=60)
    assert entry.is_allowed(now) is True


def test_seconds_until_allowed_decreases():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60, last_run=T0)
    now = T0 + timedelta(seconds=40)
    assert entry.seconds_until_allowed(now) == pytest.approx(20.0)


def test_seconds_until_allowed_zero_when_no_last_run():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60)
    assert entry.seconds_until_allowed() == 0.0


def test_seconds_until_allowed_zero_after_interval():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60, last_run=T0)
    now = T0 + timedelta(seconds=90)
    assert entry.seconds_until_allowed(now) == 0.0


def test_record_run_updates_last_run():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60)
    entry.record_run(T0)
    assert entry.last_run == T0


def test_to_dict_contains_expected_keys():
    entry = RateLimitEntry(job_name="backup", min_interval_seconds=60, last_run=T0)
    d = entry.to_dict()
    assert "job_name" in d
    assert "min_interval_seconds" in d
    assert "last_run" in d
    assert "seconds_until_allowed" in d


# --- RateLimitRegistry ---

def test_is_allowed_for_unregistered_job(registry):
    assert registry.is_allowed("unknown") is True


def test_set_limit_and_check_allowed(registry):
    registry.set_limit("nightly", 3600)
    assert registry.is_allowed("nightly") is True  # no last_run yet


def test_record_run_blocks_subsequent(registry):
    registry.set_limit("nightly", 3600)
    registry.record_run("nightly", T0)
    now = T0 + timedelta(seconds=100)
    assert registry.is_allowed("nightly", now) is False


def test_remove_limit_returns_true(registry):
    registry.set_limit("nightly", 3600)
    assert registry.remove_limit("nightly") is True


def test_remove_limit_returns_false_when_missing(registry):
    assert registry.remove_limit("ghost") is False


def test_throttled_jobs_lists_blocked(registry):
    registry.set_limit("job_a", 3600)
    registry.set_limit("job_b", 3600)
    registry.record_run("job_a", T0)
    now = T0 + timedelta(seconds=60)
    throttled = registry.throttled_jobs(now)
    assert "job_a" in throttled
    assert "job_b" not in throttled


# --- RateLimitAlertFilter ---

def _alert(job_name: str) -> Alert:
    return Alert(kind="missed", job_name=job_name, message="test")


def test_filter_forwards_when_not_throttled():
    reg = RateLimitRegistry()
    reg.set_limit("job_a", 60)
    received = []
    f = RateLimitAlertFilter(reg)
    f.add_handler(received.append)
    f(_alert("job_a"), now=T0)  # no last_run, allowed
    assert len(received) == 1


def test_filter_suppresses_when_throttled():
    reg = RateLimitRegistry()
    reg.set_limit("job_a", 3600)
    reg.record_run("job_a", T0)
    received = []
    f = RateLimitAlertFilter(reg)
    f.add_handler(received.append)
    f(_alert("job_a"), now=T0 + timedelta(seconds=10))
    assert len(received) == 0
    assert f.suppressed == 1


def test_filter_reset_suppressed():
    reg = RateLimitRegistry()
    reg.set_limit("job_a", 3600)
    reg.record_run("job_a", T0)
    f = RateLimitAlertFilter(reg)
    f.add_handler(lambda a: None)
    f(_alert("job_a"), now=T0 + timedelta(seconds=5))
    assert f.suppressed == 1
    f.reset_suppressed()
    assert f.suppressed == 0


def test_filter_forwards_unregistered_job():
    reg = RateLimitRegistry()
    received = []
    f = RateLimitAlertFilter(reg)
    f.add_handler(received.append)
    f(_alert("unknown_job"))
    assert len(received) == 1
