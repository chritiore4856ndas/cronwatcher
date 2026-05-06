"""Tests for cronwatcher.run_lock."""
import time

import pytest

from cronwatcher.run_lock import LockEntry, RunLock


@pytest.fixture()
def lock() -> RunLock:
    return RunLock()


def test_acquire_returns_true_for_new_job(lock):
    assert lock.acquire("backup") is True


def test_acquire_returns_false_when_already_locked(lock):
    lock.acquire("backup")
    assert lock.acquire("backup") is False


def test_is_locked_after_acquire(lock):
    lock.acquire("backup")
    assert lock.is_locked("backup") is True


def test_is_not_locked_before_acquire(lock):
    assert lock.is_locked("backup") is False


def test_release_removes_lock(lock):
    lock.acquire("backup")
    lock.release("backup")
    assert lock.is_locked("backup") is False


def test_release_returns_true_if_existed(lock):
    lock.acquire("backup")
    assert lock.release("backup") is True


def test_release_returns_false_if_not_locked(lock):
    assert lock.release("backup") is False


def test_get_returns_lock_entry(lock):
    lock.acquire("backup", owner_pid=1234)
    entry = lock.get("backup")
    assert isinstance(entry, LockEntry)
    assert entry.job_name == "backup"
    assert entry.owner_pid == 1234


def test_get_returns_none_when_not_locked(lock):
    assert lock.get("backup") is None


def test_held_for_increases_over_time(lock):
    lock.acquire("backup")
    time.sleep(0.05)
    entry = lock.get("backup")
    assert entry.held_for >= 0.04


def test_all_locks_returns_snapshot(lock):
    lock.acquire("job_a")
    lock.acquire("job_b")
    all_locks = lock.all_locks()
    assert set(all_locks.keys()) == {"job_a", "job_b"}


def test_release_all_clears_everything(lock):
    lock.acquire("job_a")
    lock.acquire("job_b")
    lock.release_all()
    assert lock.all_locks() == {}


def test_lock_entry_to_dict_keys():
    entry = LockEntry(job_name="sync", owner_pid=42)
    d = entry.to_dict()
    assert set(d.keys()) == {"job_name", "acquired_at", "held_for", "owner_pid"}
    assert d["owner_pid"] == 42


def test_multiple_jobs_independent(lock):
    assert lock.acquire("job_a") is True
    assert lock.acquire("job_b") is True
    lock.release("job_a")
    assert lock.is_locked("job_a") is False
    assert lock.is_locked("job_b") is True
