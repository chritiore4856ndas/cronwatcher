"""Tests for JobGroupRegistry."""
import pytest
from cronwatcher.job_grouping import JobGroup, JobGroupRegistry


@pytest.fixture
def registry() -> JobGroupRegistry:
    return JobGroupRegistry()


def test_create_group_returns_empty_group(registry):
    g = registry.create_group("batch")
    assert g.name == "batch"
    assert len(g) == 0


def test_add_to_group_stores_job(registry):
    registry.add_to_group("batch", "backup")
    assert "backup" in registry.jobs_in_group("batch")


def test_jobs_in_unknown_group_returns_empty(registry):
    assert registry.jobs_in_group("nope") == frozenset()


def test_groups_for_job_returns_all_groups(registry):
    registry.add_to_group("batch", "backup")
    registry.add_to_group("critical", "backup")
    assert registry.groups_for_job("backup") == frozenset({"batch", "critical"})


def test_groups_for_unknown_job_returns_empty(registry):
    assert registry.groups_for_job("ghost") == frozenset()


def test_remove_from_group(registry):
    registry.add_to_group("batch", "backup")
    registry.remove_from_group("batch", "backup")
    assert "backup" not in registry.jobs_in_group("batch")


def test_jobs_in_any_union(registry):
    registry.add_to_group("a", "job1")
    registry.add_to_group("b", "job2")
    result = registry.jobs_in_any(["a", "b"])
    assert result == frozenset({"job1", "job2"})


def test_jobs_in_all_intersection(registry):
    registry.add_to_group("a", "job1")
    registry.add_to_group("a", "job2")
    registry.add_to_group("b", "job2")
    result = registry.jobs_in_all(["a", "b"])
    assert result == frozenset({"job2"})


def test_jobs_in_all_empty_names_returns_empty(registry):
    registry.add_to_group("a", "job1")
    assert registry.jobs_in_all([]) == frozenset()


def test_all_groups(registry):
    registry.create_group("x")
    registry.create_group("y")
    assert registry.all_groups() == frozenset({"x", "y"})


def test_delete_group_removes_from_index(registry):
    registry.add_to_group("temp", "job1")
    registry.delete_group("temp")
    assert "temp" not in registry.all_groups()
    assert "temp" not in registry.groups_for_job("job1")


def test_create_group_idempotent(registry):
    g1 = registry.create_group("batch")
    g1.add("myjob")
    g2 = registry.create_group("batch")
    assert g2 is g1
    assert "myjob" in g2
