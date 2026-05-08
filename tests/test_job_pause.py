"""Tests for PauseRegistry and PauseEntry."""
import pytest
from cronwatcher.job_pause import PauseEntry, PauseRegistry

BASE = 1_000_000.0


@pytest.fixture
def registry():
    return PauseRegistry()


def test_pause_creates_entry(registry):
    entry = registry.pause("backup", reason="maintenance", now=BASE)
    assert entry.job_name == "backup"
    assert entry.reason == "maintenance"
    assert entry.paused_at == BASE
    assert entry.resume_at is None


def test_is_paused_indefinite(registry):
    registry.pause("backup", now=BASE)
    assert registry.is_paused("backup", now=BASE + 9999)


def test_is_paused_timed_active(registry):
    registry.pause("backup", duration_seconds=60, now=BASE)
    assert registry.is_paused("backup", now=BASE + 30)


def test_is_paused_timed_expired(registry):
    registry.pause("backup", duration_seconds=60, now=BASE)
    assert not registry.is_paused("backup", now=BASE + 61)


def test_expired_entry_auto_removed(registry):
    registry.pause("backup", duration_seconds=10, now=BASE)
    registry.is_paused("backup", now=BASE + 20)
    assert registry.get_entry("backup") is None


def test_resume_removes_entry(registry):
    registry.pause("backup", now=BASE)
    result = registry.resume("backup")
    assert result is True
    assert not registry.is_paused("backup", now=BASE)


def test_resume_unknown_job_returns_false(registry):
    assert registry.resume("nonexistent") is False


def test_all_paused_excludes_expired(registry):
    registry.pause("job_a", duration_seconds=10, now=BASE)
    registry.pause("job_b", now=BASE)  # indefinite
    paused = registry.all_paused(now=BASE + 20)
    assert "job_a" not in paused
    assert "job_b" in paused


def test_remaining_seconds_decreases():
    entry = PauseEntry(job_name="x", paused_at=BASE, resume_at=BASE + 100)
    assert entry.remaining_seconds(BASE + 40) == pytest.approx(60.0)


def test_remaining_seconds_none_for_indefinite():
    entry = PauseEntry(job_name="x", paused_at=BASE, resume_at=None)
    assert entry.remaining_seconds() is None


def test_to_dict_contains_expected_keys(registry):
    entry = registry.pause("job_c", reason="deploy", duration_seconds=30, now=BASE)
    d = entry.to_dict()
    assert set(d.keys()) == {"job_name", "paused_at", "reason", "resume_at"}


def test_reset_clears_all(registry):
    registry.pause("a", now=BASE)
    registry.pause("b", now=BASE)
    registry.reset()
    assert registry.all_paused(now=BASE) == {}
