import time
import pytest
from cronwatcher.job_tracker import JobTracker, JobRecord


def test_start_creates_running_job():
    tracker = JobTracker()
    job = tracker.start("backup")
    assert job.name == "backup"
    assert job.is_running is True
    assert job.finished_at is None


def test_finish_marks_job_done():
    tracker = JobTracker()
    tracker.start("backup")
    job = tracker.finish("backup")
    assert job is not None
    assert job.is_running is False
    assert job.finished_at is not None


def test_finish_unknown_job_returns_none():
    tracker = JobTracker()
    result = tracker.finish("nonexistent")
    assert result is None


def test_duration_increases_while_running():
    tracker = JobTracker()
    tracker.start("slow_job")
    time.sleep(0.05)
    job = tracker.get("slow_job")
    assert job.duration >= 0.05


def test_overdue_detection():
    tracker = JobTracker()
    tracker.start("quick", expected_duration=0.01)
    time.sleep(0.05)
    overdue = tracker.overdue_jobs()
    assert any(j.name == "quick" for j in overdue)


def test_not_overdue_within_limit():
    tracker = JobTracker()
    tracker.start("fast", expected_duration=10.0)
    overdue = tracker.overdue_jobs()
    assert not any(j.name == "fast" for j in overdue)


def test_missed_job_detection():
    tracker = JobTracker()
    job = tracker.start("hourly", expected_interval=1.0)
    tracker.finish("hourly")
    # Manually backdate last_seen_at to simulate missed run
    job.last_seen_at = time.time() - 5.0
    missed = tracker.missed_jobs()
    assert any(j.name == "hourly" for j in missed)


def test_no_missed_job_when_recent():
    tracker = JobTracker()
    tracker.start("frequent", expected_interval=3600.0)
    tracker.finish("frequent")
    missed = tracker.missed_jobs()
    assert not any(j.name == "frequent" for j in missed)


def test_all_jobs_returns_everything():
    tracker = JobTracker()
    tracker.start("job_a")
    tracker.start("job_b")
    tracker.finish("job_a")
    names = {j.name for j in tracker.all_jobs()}
    assert names == {"job_a", "job_b"}
