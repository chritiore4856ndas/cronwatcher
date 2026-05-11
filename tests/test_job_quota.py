"""Tests for QuotaEntry, QuotaRegistry, and QuotaAlertFilter."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert
from cronwatcher.job_quota import QuotaEntry, QuotaRegistry
from cronwatcher.quota_alert_filter import QuotaAlertFilter

T0 = datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture
def registry() -> QuotaRegistry:
    return QuotaRegistry()


# --- QuotaEntry ---

def test_entry_allowed_when_no_runs():
    entry = QuotaEntry(job_name="backup", max_runs=3, period_seconds=3600)
    assert entry.is_allowed(T0) is True


def test_entry_blocked_when_quota_reached():
    entry = QuotaEntry(job_name="backup", max_runs=2, period_seconds=3600)
    entry.record_run(T0)
    entry.record_run(T0 + timedelta(seconds=10))
    assert entry.is_allowed(T0 + timedelta(seconds=20)) is False


def test_entry_allowed_after_period_expires():
    entry = QuotaEntry(job_name="backup", max_runs=1, period_seconds=60)
    entry.record_run(T0)
    future = T0 + timedelta(seconds=61)
    assert entry.is_allowed(future) is True


def test_remaining_decreases_with_runs():
    entry = QuotaEntry(job_name="backup", max_runs=5, period_seconds=3600)
    assert entry.remaining(T0) == 5
    entry.record_run(T0)
    entry.record_run(T0 + timedelta(seconds=1))
    assert entry.remaining(T0 + timedelta(seconds=2)) == 3


def test_runs_in_period_excludes_old_runs():
    entry = QuotaEntry(job_name="backup", max_runs=10, period_seconds=60)
    entry.record_run(T0 - timedelta(seconds=120))  # outside window
    entry.record_run(T0 - timedelta(seconds=30))   # inside window
    assert entry.runs_in_period(T0) == 1


def test_to_dict_has_expected_keys():
    entry = QuotaEntry(job_name="sync", max_runs=3, period_seconds=300)
    d = entry.to_dict(T0)
    assert set(d.keys()) == {"job_name", "max_runs", "period_seconds", "runs_in_period", "remaining", "allowed"}


# --- QuotaRegistry ---

def test_get_quota_returns_none_for_unknown(registry):
    assert registry.get_quota("unknown") is None


def test_set_and_get_quota(registry):
    registry.set_quota("myjob", max_runs=5, period_seconds=3600)
    entry = registry.get_quota("myjob")
    assert entry is not None
    assert entry.max_runs == 5


def test_is_allowed_true_when_no_quota(registry):
    assert registry.is_allowed("no_quota_job", T0) is True


def test_is_allowed_false_when_quota_exceeded(registry):
    registry.set_quota("job", max_runs=1, period_seconds=3600)
    registry.record_run("job", T0)
    assert registry.is_allowed("job", T0 + timedelta(seconds=1)) is False


def test_remove_quota_returns_true(registry):
    registry.set_quota("job", max_runs=2, period_seconds=60)
    assert registry.remove_quota("job") is True
    assert registry.get_quota("job") is None


def test_remove_unknown_quota_returns_false(registry):
    assert registry.remove_quota("ghost") is False


def test_all_jobs_lists_registered(registry):
    registry.set_quota("a", 1, 60)
    registry.set_quota("b", 2, 120)
    assert set(registry.all_jobs()) == {"a", "b"}


# --- QuotaAlertFilter ---

def _alert(job: str = "myjob") -> Alert:
    return Alert(kind="overdue", job_name=job, message="test")


def test_filter_forwards_when_no_quota():
    reg = QuotaRegistry()
    sink = MagicMock()
    f = QuotaAlertFilter(reg)
    f.add_handler(sink)
    f(_alert())
    sink.assert_called_once()


def test_filter_forwards_when_quota_remaining():
    reg = QuotaRegistry()
    reg.set_quota("myjob", max_runs=3, period_seconds=3600)
    sink = MagicMock()
    f = QuotaAlertFilter(reg)
    f.add_handler(sink)
    f(_alert())
    sink.assert_called_once()


def test_filter_suppresses_when_quota_exceeded():
    reg = QuotaRegistry()
    reg.set_quota("myjob", max_runs=1, period_seconds=3600)
    reg.record_run("myjob", T0)
    sink = MagicMock()
    f = QuotaAlertFilter(reg)
    f.add_handler(sink)
    f(_alert())
    sink.assert_not_called()
    assert f.suppressed == 1


def test_reset_suppressed_clears_count():
    reg = QuotaRegistry()
    reg.set_quota("myjob", max_runs=0, period_seconds=3600)
    f = QuotaAlertFilter(reg)
    f(_alert())
    assert f.suppressed == 1
    f.reset_suppressed()
    assert f.suppressed == 0
