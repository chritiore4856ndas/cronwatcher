"""Tests for the MetricsCollector and JobMetrics."""
import pytest

from cronwatcher.metrics import JobMetrics, MetricsCollector


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector()


def test_record_run_increments_count(collector: MetricsCollector) -> None:
    collector.record_run("backup", 12.5)
    collector.record_run("backup", 8.0)
    m = collector.get("backup")
    assert m is not None
    assert m.run_count == 2


def test_avg_duration_calculated_correctly(collector: MetricsCollector) -> None:
    collector.record_run("backup", 10.0)
    collector.record_run("backup", 20.0)
    m = collector.get("backup")
    assert m.avg_duration == pytest.approx(15.0)


def test_max_duration(collector: MetricsCollector) -> None:
    collector.record_run("sync", 5.0)
    collector.record_run("sync", 99.0)
    collector.record_run("sync", 3.0)
    assert collector.get("sync").max_duration == pytest.approx(99.0)


def test_no_durations_returns_none() -> None:
    m = JobMetrics(job_name="empty")
    assert m.avg_duration is None
    assert m.max_duration is None


def test_record_miss(collector: MetricsCollector) -> None:
    collector.record_miss("nightly")
    collector.record_miss("nightly")
    assert collector.get("nightly").miss_count == 2


def test_record_overdue(collector: MetricsCollector) -> None:
    collector.record_overdue("report")
    assert collector.get("report").overdue_count == 1


def test_get_unknown_job_returns_none(collector: MetricsCollector) -> None:
    assert collector.get("ghost") is None


def test_all_returns_all_jobs(collector: MetricsCollector) -> None:
    collector.record_run("a", 1.0)
    collector.record_run("b", 2.0)
    names = {d["job_name"] for d in collector.all()}
    assert names == {"a", "b"}


def test_to_dict_shape(collector: MetricsCollector) -> None:
    collector.record_run("x", 7.0)
    collector.record_miss("x")
    d = collector.get("x").to_dict()
    assert set(d.keys()) == {
        "job_name", "run_count", "miss_count",
        "overdue_count", "avg_duration_seconds", "max_duration_seconds",
    }


def test_reset_single_job(collector: MetricsCollector) -> None:
    collector.record_run("a", 1.0)
    collector.record_run("b", 2.0)
    collector.reset("a")
    assert collector.get("a") is None
    assert collector.get("b") is not None


def test_reset_all(collector: MetricsCollector) -> None:
    collector.record_run("a", 1.0)
    collector.record_run("b", 2.0)
    collector.reset()
    assert collector.all() == []
