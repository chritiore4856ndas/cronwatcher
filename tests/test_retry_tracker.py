"""Tests for RetryTracker and RetryRecord."""
import pytest
from cronwatcher.retry_tracker import RetryTracker, RetryRecord


def test_get_or_create_returns_new_record():
    tracker = RetryTracker(max_retries=3)
    record = tracker.get_or_create("backup")
    assert isinstance(record, RetryRecord)
    assert record.job_name == "backup"
    assert record.attempts == 0


def test_get_or_create_returns_same_instance():
    tracker = RetryTracker(max_retries=3)
    r1 = tracker.get_or_create("backup")
    r2 = tracker.get_or_create("backup")
    assert r1 is r2


def test_record_attempt_increments_count():
    tracker = RetryTracker(max_retries=3)
    tracker.record_attempt("backup")
    tracker.record_attempt("backup")
    assert tracker.get_or_create("backup").attempts == 2


def test_record_attempt_stores_history():
    tracker = RetryTracker(max_retries=3)
    tracker.record_attempt("backup")
    tracker.record_attempt("backup")
    assert len(tracker.get_or_create("backup").history) == 2


def test_is_exhausted_false_below_limit():
    tracker = RetryTracker(max_retries=3)
    tracker.record_attempt("backup")
    tracker.record_attempt("backup")
    assert tracker.is_exhausted("backup") is False


def test_is_exhausted_true_at_limit():
    tracker = RetryTracker(max_retries=3)
    for _ in range(3):
        tracker.record_attempt("backup")
    assert tracker.is_exhausted("backup") is True


def test_is_exhausted_unknown_job_returns_false():
    tracker = RetryTracker(max_retries=3)
    assert tracker.is_exhausted("ghost") is False


def test_reset_removes_record():
    tracker = RetryTracker(max_retries=3)
    tracker.record_attempt("backup")
    tracker.reset("backup")
    assert "backup" not in tracker.all_records()


def test_mark_success_sets_flag():
    tracker = RetryTracker(max_retries=3)
    tracker.record_attempt("backup")
    tracker.mark_success("backup")
    assert tracker.get_or_create("backup").succeeded is True
