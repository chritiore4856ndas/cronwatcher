"""Tests for WindowAlertFilter."""
from datetime import datetime, time
from typing import List

import pytest

from cronwatcher.alert_manager import Alert
from cronwatcher.job_window import WindowRegistry
from cronwatcher.window_alert_filter import WindowAlertFilter


class _Sink:
    def __init__(self) -> None:
        self.received: List[Alert] = []

    def __call__(self, alert: Alert) -> None:
        self.received.append(alert)


def _alert(job_name: str = "myjob", kind: str = "missed") -> Alert:
    return Alert(kind=kind, job_name=job_name, message="test")


@pytest.fixture()
def registry() -> WindowRegistry:
    return WindowRegistry()


@pytest.fixture()
def sink() -> _Sink:
    return _Sink()


@pytest.fixture()
def wfilter(registry, sink) -> WindowAlertFilter:
    f = WindowAlertFilter(registry=registry)
    f.add_handler(sink)
    return f


def test_no_window_forwards_alert(wfilter, sink):
    alert = _alert("unrestricted")
    wfilter(alert)
    assert len(sink.received) == 1


def test_alert_forwarded_within_window(wfilter, registry, sink):
    registry.set_window("myjob", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 10, 0)  # inside window
    wfilter(_alert("myjob"), at=at)
    assert len(sink.received) == 1


def test_alert_suppressed_outside_window(wfilter, registry, sink):
    registry.set_window("myjob", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 22, 0)  # outside window
    wfilter(_alert("myjob"), at=at)
    assert len(sink.received) == 0


def test_suppressed_counter_increments(wfilter, registry):
    registry.set_window("myjob", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 22, 0)
    wfilter(_alert("myjob"), at=at)
    wfilter(_alert("myjob"), at=at)
    assert wfilter.suppressed == 2


def test_reset_suppressed(wfilter, registry):
    registry.set_window("myjob", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 22, 0)
    wfilter(_alert("myjob"), at=at)
    wfilter.reset_suppressed()
    assert wfilter.suppressed == 0


def test_multiple_handlers_all_called(registry):
    sink1, sink2 = _Sink(), _Sink()
    f = WindowAlertFilter(registry=registry)
    f.add_handler(sink1)
    f.add_handler(sink2)
    f(_alert("job"))
    assert len(sink1.received) == 1
    assert len(sink2.received) == 1


def test_only_matching_job_suppressed(wfilter, registry, sink):
    registry.set_window("restricted", time(8, 0), time(18, 0))
    at = datetime(2024, 6, 3, 22, 0)
    wfilter(_alert("other_job"), at=at)   # no window -> forwarded
    wfilter(_alert("restricted"), at=at)  # outside window -> suppressed
    assert len(sink.received) == 1
    assert sink.received[0].job_name == "other_job"
