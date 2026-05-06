"""Tests for cronwatcher.job_tags."""
import pytest

from cronwatcher.job_tags import TagRegistry


@pytest.fixture()
def registry() -> TagRegistry:
    reg = TagRegistry()
    reg.register("backup", ["critical", "nightly"])
    reg.register("report", ["nightly", "email"])
    reg.register("cleanup", ["maintenance"])
    return reg


def test_jobs_for_single_tag(registry: TagRegistry) -> None:
    assert registry.jobs_for_tag("nightly") == {"backup", "report"}


def test_jobs_for_tag_case_insensitive(registry: TagRegistry) -> None:
    assert registry.jobs_for_tag("CRITICAL") == {"backup"}


def test_jobs_for_tags_union(registry: TagRegistry) -> None:
    result = registry.jobs_for_tags(["critical", "email"])
    assert result == {"backup", "report"}


def test_jobs_for_tags_intersection(registry: TagRegistry) -> None:
    result = registry.jobs_for_tags(["critical", "nightly"], match_all=True)
    assert result == {"backup"}


def test_jobs_for_tags_no_intersection(registry: TagRegistry) -> None:
    result = registry.jobs_for_tags(["critical", "email"], match_all=True)
    assert result == set()


def test_tags_for_job(registry: TagRegistry) -> None:
    assert registry.tags_for_job("backup") == {"critical", "nightly"}


def test_tags_for_unknown_job_returns_empty(registry: TagRegistry) -> None:
    assert registry.tags_for_job("ghost") == set()


def test_all_tags_sorted(registry: TagRegistry) -> None:
    assert registry.all_tags() == ["critical", "email", "maintenance", "nightly"]


def test_remove_job_cleans_tags(registry: TagRegistry) -> None:
    registry.remove_job("backup")
    assert "backup" not in registry.jobs_for_tag("nightly")
    assert "backup" not in registry.jobs_for_tag("critical")
    # 'critical' tag should be gone entirely
    assert "critical" not in registry.all_tags()


def test_remove_unknown_job_is_noop(registry: TagRegistry) -> None:
    registry.remove_job("does_not_exist")  # should not raise


def test_empty_tags_ignored() -> None:
    reg = TagRegistry()
    reg.register("job", ["", "  ", "valid"])
    assert reg.tags_for_job("job") == {"valid"}


def test_jobs_for_empty_tags_returns_empty(registry: TagRegistry) -> None:
    assert registry.jobs_for_tags([]) == set()


def test_to_dict(registry: TagRegistry) -> None:
    d = registry.to_dict()
    assert set(d.keys()) == {"backup", "report", "cleanup"}
    assert d["backup"] == ["critical", "nightly"]
    assert d["report"] == ["email", "nightly"]
