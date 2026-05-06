"""Tests for cronwatcher.job_history."""
import time

import pytest

from cronwatcher.job_history import JobHistory, RunEntry


@pytest.fixture()
def history() -> JobHistory:
    return JobHistory(maxlen=5)


# ---------------------------------------------------------------------------
# RunEntry
# ---------------------------------------------------------------------------

def test_run_entry_duration_none_while_running():
    entry = RunEntry(job_name="backup", started_at=1000.0)
    assert entry.duration is None


def test_run_entry_duration_after_finish():
    entry = RunEntry(job_name="backup", started_at=1000.0, finished_at=1030.0)
    assert entry.duration == pytest.approx(30.0)


def test_run_entry_to_dict_keys():
    entry = RunEntry(job_name="sync", started_at=500.0, finished_at=510.0)
    d = entry.to_dict()
    assert set(d.keys()) == {"job", "started_at", "finished_at", "duration", "exit_ok"}
    assert d["job"] == "sync"


# ---------------------------------------------------------------------------
# JobHistory.record_start / record_finish
# ---------------------------------------------------------------------------

def test_record_start_returns_entry(history):
    entry = history.record_start("nightly")
    assert isinstance(entry, RunEntry)
    assert entry.job_name == "nightly"
    assert entry.finished_at is None


def test_record_finish_sets_timestamp(history):
    history.record_start("nightly", started_at=1000.0)
    entry = history.record_finish("nightly", finished_at=1020.0)
    assert entry is not None
    assert entry.finished_at == pytest.approx(1020.0)


def test_record_finish_unknown_job_returns_none(history):
    result = history.record_finish("ghost")
    assert result is None


def test_record_finish_marks_exit_status(history):
    history.record_start("deploy")
    entry = history.record_finish("deploy", exit_ok=False)
    assert entry.exit_ok is False


# ---------------------------------------------------------------------------
# get / last
# ---------------------------------------------------------------------------

def test_get_returns_all_entries(history):
    history.record_start("job", started_at=1.0)
    history.record_start("job", started_at=2.0)
    assert len(history.get("job")) == 2


def test_last_returns_most_recent(history):
    history.record_start("job", started_at=1.0)
    history.record_start("job", started_at=2.0)
    assert history.last("job").started_at == pytest.approx(2.0)


def test_last_unknown_job_returns_none(history):
    assert history.last("unknown") is None


# ---------------------------------------------------------------------------
# rolling window
# ---------------------------------------------------------------------------

def test_maxlen_is_respected():
    h = JobHistory(maxlen=3)
    for i in range(6):
        h.record_start("job", started_at=float(i))
    entries = h.get("job")
    assert len(entries) == 3
    assert entries[0].started_at == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# failure_rate / all_jobs / clear
# ---------------------------------------------------------------------------

def test_failure_rate_all_ok(history):
    history.record_start("j")
    history.record_finish("j", exit_ok=True)
    assert history.failure_rate("j") == pytest.approx(0.0)


def test_failure_rate_mixed(history):
    for ok in [True, False, False, True]:
        history.record_start("j")
        history.record_finish("j", exit_ok=ok)
    assert history.failure_rate("j") == pytest.approx(0.5)


def test_all_jobs_lists_tracked_names(history):
    history.record_start("alpha")
    history.record_start("beta")
    assert set(history.all_jobs()) == {"alpha", "beta"}


def test_clear_removes_job(history):
    history.record_start("tmp")
    history.clear("tmp")
    assert history.get("tmp") == []
