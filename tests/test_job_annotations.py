"""Tests for AnnotationRegistry."""
from __future__ import annotations

import pytest

from cronwatcher.job_annotations import AnnotationRegistry


@pytest.fixture()
def registry() -> AnnotationRegistry:
    return AnnotationRegistry()


def test_annotate_and_get(registry):
    registry.annotate("backup", "owner", "alice")
    assert registry.get("backup", "owner") == "alice"


def test_get_missing_key_returns_default(registry):
    assert registry.get("backup", "owner") is None
    assert registry.get("backup", "owner", "unknown") == "unknown"


def test_set_annotations_merges(registry):
    registry.annotate("backup", "owner", "alice")
    registry.set_annotations("backup", {"team": "ops", "priority": 1})
    assert registry.get("backup", "owner") == "alice"
    assert registry.get("backup", "team") == "ops"
    assert registry.get("backup", "priority") == 1


def test_get_all_returns_copy(registry):
    registry.annotate("backup", "owner", "alice")
    result = registry.get_all("backup")
    result["owner"] = "MUTATED"
    assert registry.get("backup", "owner") == "alice"


def test_remove_existing_key(registry):
    registry.annotate("backup", "owner", "alice")
    removed = registry.remove("backup", "owner")
    assert removed is True
    assert registry.get("backup", "owner") is None


def test_remove_nonexistent_key_returns_false(registry):
    assert registry.remove("backup", "missing") is False


def test_jobs_with_annotation_key_only(registry):
    registry.annotate("backup", "env", "prod")
    registry.annotate("report", "env", "staging")
    registry.annotate("cleanup", "owner", "bob")
    result = set(registry.jobs_with_annotation("env"))
    assert result == {"backup", "report"}


def test_jobs_with_annotation_key_and_value(registry):
    registry.annotate("backup", "env", "prod")
    registry.annotate("report", "env", "staging")
    result = list(registry.jobs_with_annotation("env", "prod"))
    assert result == ["backup"]


def test_clear_removes_all_annotations(registry):
    registry.set_annotations("backup", {"owner": "alice", "env": "prod"})
    registry.clear("backup")
    assert registry.get_all("backup") == {}


def test_clear_unknown_job_is_noop(registry):
    registry.clear("nonexistent")  # should not raise
