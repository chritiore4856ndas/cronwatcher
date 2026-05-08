"""Tests for PauseAlertFilter."""
import pytest
from cronwatcher.alert_manager import Alert
from cronwatcher.job_pause import PauseRegistry
from cronwatcher.pause_alert_filter import PauseAlertFilter

BASE = 1_000_000.0


class _Sink:
    def __init__(self):
        self.received: list = []

    def __call__(self, alert: Alert):
        self.received.append(alert)


def _alert(job_name: str, kind: str = "missed") -> Alert:
    return Alert(job_name=job_name, kind=kind, message="test")


@pytest.fixture
def registry():
    return PauseRegistry()


@pytest.fixture
def sink():
    return _Sink()


@pytest.fixture
def pfilter(registry, sink):
    f = PauseAlertFilter(registry)
    f.add_handler(sink)
    return f


def test_alert_forwarded_when_not_paused(pfilter, sink):
    pfilter(_alert("job_a"))
    assert len(sink.received) == 1


def test_alert_suppressed_when_paused(registry, pfilter, sink):
    registry.pause("job_a", now=BASE)
    pfilter(_alert("job_a"))
    assert len(sink.received) == 0


def test_suppressed_count_increments(registry, pfilter):
    registry.pause("job_a", now=BASE)
    pfilter(_alert("job_a"))
    pfilter(_alert("job_a"))
    assert pfilter.suppressed_count("job_a") == 2


def test_suppressed_count_all_jobs(registry, pfilter):
    registry.pause("job_a", now=BASE)
    registry.pause("job_b", now=BASE)
    pfilter(_alert("job_a"))
    pfilter(_alert("job_b"))
    assert pfilter.suppressed_count() == 2


def test_alert_forwarded_after_resume(registry, pfilter, sink):
    registry.pause("job_a", now=BASE)
    registry.resume("job_a")
    pfilter(_alert("job_a"))
    assert len(sink.received) == 1


def test_alert_forwarded_after_timed_pause_expires(registry, pfilter, sink, monkeypatch):
    import time
    registry.pause("job_a", duration_seconds=10, now=BASE)
    monkeypatch.setattr(time, "time", lambda: BASE + 20)
    pfilter(_alert("job_a"))
    assert len(sink.received) == 1


def test_different_jobs_independent(registry, pfilter, sink):
    registry.pause("job_a", now=BASE)
    pfilter(_alert("job_a"))
    pfilter(_alert("job_b"))
    assert len(sink.received) == 1
    assert sink.received[0].job_name == "job_b"


def test_clear_suppressed(registry, pfilter):
    registry.pause("job_a", now=BASE)
    pfilter(_alert("job_a"))
    pfilter.clear_suppressed()
    assert pfilter.suppressed_count() == 0
