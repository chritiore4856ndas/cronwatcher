"""Tests for GroupAlertFilter."""
from __future__ import annotations

from datetime import datetime
from typing import List

import pytest

from cronwatcher.alert_manager import Alert
from cronwatcher.group_alert_filter import GroupAlertFilter
from cronwatcher.job_grouping import JobGroupRegistry


class _Sink:
    def __init__(self):
        self.received: List[Alert] = []

    def __call__(self, alert: Alert) -> None:
        self.received.append(alert)


def _alert(job_name: str) -> Alert:
    return Alert(kind="missed", job_name=job_name, message="test", timestamp=datetime.utcnow())


@pytest.fixture
def registry() -> JobGroupRegistry:
    return JobGroupRegistry()


@pytest.fixture
def sink() -> _Sink:
    return _Sink()


@pytest.fixture
def gfilter(registry, sink) -> GroupAlertFilter:
    f = GroupAlertFilter(registry=registry)
    f.add_handler(sink)
    return f


def test_no_filter_forwards_all(gfilter, sink):
    gfilter(_alert("any_job"))
    assert len(sink.received) == 1


def test_job_in_allowed_group_is_forwarded(gfilter, registry, sink):
    registry.add_to_group("critical", "backup")
    gfilter.configure(["critical"])
    gfilter(_alert("backup"))
    assert len(sink.received) == 1


def test_job_not_in_allowed_group_is_blocked(gfilter, registry, sink):
    registry.add_to_group("batch", "cleanup")
    gfilter.configure(["critical"])
    gfilter(_alert("cleanup"))
    assert len(sink.received) == 0


def test_job_in_multiple_groups_passes_if_one_matches(gfilter, registry, sink):
    registry.add_to_group("batch", "etl")
    registry.add_to_group("critical", "etl")
    gfilter.configure(["critical"])
    gfilter(_alert("etl"))
    assert len(sink.received) == 1


def test_unknown_job_blocked_when_filter_configured(gfilter, sink):
    gfilter.configure(["critical"])
    gfilter(_alert("unknown_job"))
    assert len(sink.received) == 0


def test_multiple_handlers_all_called(registry):
    s1, s2 = _Sink(), _Sink()
    registry.add_to_group("g", "job1")
    f = GroupAlertFilter(registry=registry)
    f.add_handler(s1)
    f.add_handler(s2)
    f.configure(["g"])
    f(_alert("job1"))
    assert len(s1.received) == 1
    assert len(s2.received) == 1


def test_reconfigure_changes_filter(gfilter, registry, sink):
    registry.add_to_group("a", "job_a")
    registry.add_to_group("b", "job_b")
    gfilter.configure(["a"])
    gfilter(_alert("job_b"))
    assert len(sink.received) == 0
    gfilter.configure(["b"])
    gfilter(_alert("job_b"))
    assert len(sink.received) == 1
