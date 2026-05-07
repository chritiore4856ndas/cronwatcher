"""Tests for LabelRegistry and LabelAlertFilter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert
from cronwatcher.job_labels import LabelRegistry
from cronwatcher.label_alert_filter import LabelAlertFilter


@pytest.fixture()
def registry() -> LabelRegistry:
    r = LabelRegistry()
    r.set_labels("backup", {"env": "prod", "team": "ops"})
    r.set_labels("report", {"env": "prod", "team": "data"})
    r.set_labels("cleanup", {"env": "staging", "team": "ops"})
    return r


def test_get_labels_returns_set_values(registry: LabelRegistry) -> None:
    assert registry.get_labels("backup") == {"env": "prod", "team": "ops"}


def test_get_labels_unknown_job_returns_empty(registry: LabelRegistry) -> None:
    assert registry.get_labels("nonexistent") == {}


def test_jobs_with_label_key_only(registry: LabelRegistry) -> None:
    result = registry.jobs_with_label("env")
    assert result == {"backup", "report", "cleanup"}


def test_jobs_with_label_key_and_value(registry: LabelRegistry) -> None:
    result = registry.jobs_with_label("env", "prod")
    assert result == {"backup", "report"}


def test_jobs_with_label_no_match(registry: LabelRegistry) -> None:
    assert registry.jobs_with_label("env", "dev") == set()


def test_jobs_matching_all_single_label(registry: LabelRegistry) -> None:
    result = registry.jobs_matching_all({"team": "ops"})
    assert result == {"backup", "cleanup"}


def test_jobs_matching_all_multiple_labels(registry: LabelRegistry) -> None:
    result = registry.jobs_matching_all({"env": "prod", "team": "ops"})
    assert result == {"backup"}


def test_jobs_matching_all_empty_selector_returns_all(registry: LabelRegistry) -> None:
    assert registry.jobs_matching_all({}) == {"backup", "report", "cleanup"}


def test_set_labels_replaces_old_values(registry: LabelRegistry) -> None:
    registry.set_labels("backup", {"env": "staging"})
    assert registry.get_labels("backup") == {"env": "staging"}
    # old index entries should be gone
    assert "backup" not in registry.jobs_with_label("team", "ops")


def test_remove_job_clears_labels(registry: LabelRegistry) -> None:
    registry.remove_job("backup")
    assert registry.get_labels("backup") == {}
    assert "backup" not in registry.all_jobs()


# --- LabelAlertFilter tests ---

def _alert(job: str) -> Alert:
    return Alert(kind="missed", job_name=job, message="test")


@pytest.fixture()
def downstream() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def label_filter(registry: LabelRegistry, downstream: MagicMock) -> LabelAlertFilter:
    return LabelAlertFilter(registry=registry, downstream=downstream)


def test_no_selector_forwards_all(label_filter: LabelAlertFilter, downstream: MagicMock) -> None:
    label_filter(_alert("backup"))
    label_filter(_alert("cleanup"))
    assert downstream.call_count == 2


def test_selector_forwards_matching_job(label_filter: LabelAlertFilter, downstream: MagicMock) -> None:
    label_filter.configure({"env": "prod"})
    label_filter(_alert("backup"))
    downstream.assert_called_once()


def test_selector_blocks_non_matching_job(label_filter: LabelAlertFilter, downstream: MagicMock) -> None:
    label_filter.configure({"env": "prod"})
    label_filter(_alert("cleanup"))  # cleanup is staging
    downstream.assert_not_called()


def test_configure_updates_selector(label_filter: LabelAlertFilter, downstream: MagicMock) -> None:
    label_filter.configure({"team": "data"})
    label_filter(_alert("backup"))  # ops team, should be blocked
    assert downstream.call_count == 0
    label_filter.configure({"team": "ops"})
    label_filter(_alert("backup"))  # now matches
    assert downstream.call_count == 1
