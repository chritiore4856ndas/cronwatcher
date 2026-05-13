"""Tests for job suppression registry and alert filter."""
from __future__ import annotations

import time
import pytest

from cronwatcher.job_suppression import SuppressionRegistry, SuppressionEntry
from cronwatcher.suppression_alert_filter import SuppressionAlertFilter
from cronwatcher.alert_manager import Alert


@pytest.fixture()
def registry() -> SuppressionRegistry:
    return SuppressionRegistry()


def _alert(job: str = "backup") -> Alert:
    return Alert(kind="missed", job_name=job, message="test alert")


# --- SuppressionEntry ---

def test_entry_is_active_indefinite():
    entry = SuppressionEntry(job_name="x", reason="manual", expires_at=None)
    assert entry.is_active() is True


def test_entry_is_active_before_expiry():
    future = time.time() + 60
    entry = SuppressionEntry(job_name="x", reason="manual", expires_at=future)
    assert entry.is_active() is True


def test_entry_is_inactive_after_expiry():
    past = time.time() - 1
    entry = SuppressionEntry(job_name="x", reason="manual", expires_at=past)
    assert entry.is_active() is False


def test_remaining_seconds_none_for_indefinite():
    entry = SuppressionEntry(job_name="x", reason="r", expires_at=None)
    assert entry.remaining_seconds() is None


def test_remaining_seconds_positive_before_expiry():
    future = time.time() + 30
    entry = SuppressionEntry(job_name="x", reason="r", expires_at=future)
    assert entry.remaining_seconds() > 0


# --- SuppressionRegistry ---

def test_suppress_creates_entry(registry):
    entry = registry.suppress("backup", "maintenance")
    assert isinstance(entry, SuppressionEntry)
    assert registry.is_suppressed("backup")


def test_lift_removes_suppression(registry):
    registry.suppress("backup", "maintenance")
    result = registry.lift("backup")
    assert result is True
    assert not registry.is_suppressed("backup")


def test_lift_unknown_job_returns_false(registry):
    assert registry.lift("nonexistent") is False


def test_timed_suppression_expires(registry):
    past = time.time() - 1
    registry._entries["backup"] = SuppressionEntry(
        job_name="backup", reason="expired", expires_at=past
    )
    assert not registry.is_suppressed("backup")
    # auto-pruned
    assert registry.get("backup") is None


def test_all_suppressed_prunes_expired(registry):
    now = time.time()
    registry._entries["active"] = SuppressionEntry("active", "r", expires_at=now + 60)
    registry._entries["expired"] = SuppressionEntry("expired", "r", expires_at=now - 1)
    active = registry.all_suppressed()
    assert "active" in active
    assert "expired" not in active


def test_reset_clears_all(registry):
    registry.suppress("a", "r")
    registry.suppress("b", "r")
    registry.reset()
    assert registry.all_suppressed() == {}


# --- SuppressionAlertFilter ---

def test_filter_forwards_non_suppressed_alert(registry):
    received = []
    f = SuppressionAlertFilter(registry)
    f.add_handler(received.append)
    f(_alert("backup"))
    assert len(received) == 1


def test_filter_drops_suppressed_alert(registry):
    received = []
    registry.suppress("backup", "maintenance")
    f = SuppressionAlertFilter(registry)
    f.add_handler(received.append)
    f(_alert("backup"))
    assert received == []
    assert f.suppressed_count == 1


def test_filter_counts_multiple_suppressions(registry):
    received = []
    registry.suppress("backup", "maint")
    f = SuppressionAlertFilter(registry)
    f.add_handler(received.append)
    f(_alert("backup"))
    f(_alert("backup"))
    assert f.suppressed_count == 2


def test_reset_suppressed_count(registry):
    registry.suppress("backup", "maint")
    f = SuppressionAlertFilter(registry)
    f.add_handler(lambda a: None)
    f(_alert("backup"))
    f.reset_suppressed_count()
    assert f.suppressed_count == 0
