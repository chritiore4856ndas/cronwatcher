"""Tests for JobStatusExporter."""
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock

from cronwatcher.job_status_exporter import JobStatusExporter, JobStatusSnapshot
from cronwatcher.job_tracker import JobTracker
from cronwatcher.job_history import JobHistory
from cronwatcher.schedule_parser import CronSchedule


@pytest.fixture
def tracker():
    return JobTracker()


@pytest.fixture
def history():
    return JobHistory()


@pytest.fixture
def exporter(tracker, history):
    return JobStatusExporter(tracker=tracker, history=history)


def test_export_unknown_job_returns_none(exporter):
    assert exporter.export_job("ghost") is None


def test_export_job_after_start(exporter, tracker, history):
    tracker.start("backup")
    history.record_start("backup")
    snap = exporter.export_job("backup")
    assert snap is not None
    assert snap.job_name == "backup"
    assert snap.is_running is True
    assert snap.run_count == 1


def test_export_job_after_finish(exporter, tracker, history):
    tracker.start("backup")
    entry = history.record_start("backup")
    time.sleep(0.01)
    tracker.finish("backup", exit_code=0)
    history.record_finish("backup", exit_code=0)
    snap = exporter.export_job("backup")
    assert snap.is_running is False
    assert snap.last_exit_code == 0
    assert snap.last_duration is not None
    assert snap.last_duration >= 0


def test_to_dict_has_expected_keys(exporter, tracker, history):
    tracker.start("sync")
    history.record_start("sync")
    snap = exporter.export_job("sync")
    d = snap.to_dict()
    expected_keys = {
        "job_name", "is_running", "last_start", "last_finish",
        "last_duration", "last_exit_code", "run_count",
        "schedule_expr", "is_missed",
    }
    assert expected_keys == set(d.keys())


def test_export_all_returns_all_known_jobs(exporter, tracker, history):
    for name in ("job_a", "job_b", "job_c"):
        tracker.start(name)
        history.record_start(name)
    snaps = exporter.export_all()
    names = [s.job_name for s in snaps]
    assert "job_a" in names
    assert "job_b" in names
    assert "job_c" in names


def test_jobs_currently_running(exporter, tracker, history):
    tracker.start("active")
    history.record_start("active")
    tracker.start("done")
    history.record_start("done")
    tracker.finish("done", exit_code=0)
    history.record_finish("done", exit_code=0)
    running = exporter.jobs_currently_running()
    assert "active" in running
    assert "done" not in running


def test_schedule_is_attached_to_snapshot(exporter, tracker, history):
    schedule = MagicMock(spec=CronSchedule)
    schedule.expression = "*/5 * * * *"
    schedule.is_missed.return_value = False
    exporter.register_schedule("report", schedule)
    tracker.start("report")
    history.record_start("report")
    snap = exporter.export_job("report")
    assert snap.schedule_expr == "*/5 * * * *"
    assert snap.is_missed is False


def test_jobs_missed_uses_schedule(exporter, tracker, history):
    missed_schedule = MagicMock(spec=CronSchedule)
    missed_schedule.expression = "0 * * * *"
    missed_schedule.is_missed.return_value = True
    exporter.register_schedule("hourly", missed_schedule)
    history.record_start("hourly")
    missed = exporter.jobs_missed()
    assert "hourly" in missed
