"""Tests for AnnotationAlertFilter and AnnotationExporter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from cronwatcher.alert_manager import Alert
from cronwatcher.annotation_alert_filter import AnnotationAlertFilter
from cronwatcher.annotation_exporter import AnnotationExporter
from cronwatcher.job_annotations import AnnotationRegistry


@dataclass
class _Sink:
    received: List[Alert] = field(default_factory=list)

    def __call__(self, alert: Alert) -> None:
        self.received.append(alert)


def _alert(job: str) -> Alert:
    return Alert(kind="missed", job_name=job, message=f"{job} missed")


@pytest.fixture()
def registry() -> AnnotationRegistry:
    reg = AnnotationRegistry()
    reg.annotate("backup", "env", "prod")
    reg.annotate("report", "env", "staging")
    reg.annotate("cleanup", "owner", "bob")
    return reg


def test_filter_forwards_matching_key(registry):
    sink = _Sink()
    f = AnnotationAlertFilter(registry=registry, key="env")
    f.add_handler(sink)
    f(_alert("backup"))
    f(_alert("report"))
    assert len(sink.received) == 2


def test_filter_blocks_non_annotated_job(registry):
    sink = _Sink()
    f = AnnotationAlertFilter(registry=registry, key="env")
    f.add_handler(sink)
    f(_alert("cleanup"))  # has 'owner', not 'env'
    assert sink.received == []


def test_filter_matches_key_and_value(registry):
    sink = _Sink()
    f = AnnotationAlertFilter(registry=registry, key="env", value="prod")
    f.add_handler(sink)
    f(_alert("backup"))
    f(_alert("report"))  # env=staging, should be blocked
    assert len(sink.received) == 1
    assert sink.received[0].job_name == "backup"


def test_multiple_downstream_handlers(registry):
    sink1, sink2 = _Sink(), _Sink()
    f = AnnotationAlertFilter(registry=registry, key="env")
    f.add_handler(sink1)
    f.add_handler(sink2)
    f(_alert("backup"))
    assert len(sink1.received) == 1
    assert len(sink2.received) == 1


# --- AnnotationExporter ---

def test_exporter_export_job(registry):
    exp = AnnotationExporter(registry)
    result = exp.export_job("backup")
    assert result["job"] == "backup"
    assert result["annotations"]["env"] == "prod"


def test_exporter_export_all(registry):
    exp = AnnotationExporter(registry)
    results = exp.export_all(["backup", "report"])
    assert len(results) == 2
    jobs = {r["job"] for r in results}
    assert jobs == {"backup", "report"}


def test_exporter_jobs_with_key(registry):
    exp = AnnotationExporter(registry)
    jobs = exp.jobs_with_key("env")
    assert set(jobs) == {"backup", "report"}


def test_exporter_jobs_with_key_and_value(registry):
    exp = AnnotationExporter(registry)
    jobs = exp.jobs_with_key("env", "staging")
    assert jobs == ["report"]
