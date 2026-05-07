import pytest
from cronwatcher.job_priority import Priority, PriorityRegistry


@pytest.fixture
def registry():
    return PriorityRegistry()


def test_default_priority_is_normal(registry):
    assert registry.get_priority("backup") == Priority.NORMAL


def test_set_and_get_priority(registry):
    registry.set_priority("cleanup", Priority.HIGH)
    assert registry.get_priority("cleanup") == Priority.HIGH


def test_set_priority_from_string(registry):
    registry.set_priority("deploy", "critical")
    assert registry.get_priority("deploy") == Priority.CRITICAL


def test_invalid_priority_string_raises(registry):
    with pytest.raises(ValueError, match="Unknown priority"):
        registry.set_priority("job", "urgent")


def test_jobs_at_returns_correct_names(registry):
    registry.set_priority("a", Priority.HIGH)
    registry.set_priority("b", Priority.LOW)
    registry.set_priority("c", Priority.HIGH)
    result = registry.jobs_at(Priority.HIGH)
    assert set(result) == {"a", "c"}


def test_jobs_at_from_string(registry):
    registry.set_priority("x", Priority.LOW)
    assert "x" in registry.jobs_at("low")


def test_jobs_above_threshold(registry):
    registry.set_priority("low_job", Priority.LOW)
    registry.set_priority("high_job", Priority.HIGH)
    registry.set_priority("critical_job", Priority.CRITICAL)
    result = registry.jobs_above(Priority.NORMAL)
    assert set(result) == {"high_job", "critical_job"}


def test_all_priorities_snapshot(registry):
    registry.set_priority("job1", Priority.NORMAL)
    registry.set_priority("job2", Priority.LOW)
    snap = registry.all_priorities()
    assert snap == {"job1": "NORMAL", "job2": "LOW"}


def test_reset_clears_all(registry):
    registry.set_priority("job", Priority.CRITICAL)
    registry.reset()
    assert registry.get_priority("job") == Priority.NORMAL
    assert registry.all_priorities() == {}


def test_priority_ordering():
    assert Priority.LOW < Priority.NORMAL < Priority.HIGH < Priority.CRITICAL
