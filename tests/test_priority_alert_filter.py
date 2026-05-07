import pytest
from unittest.mock import MagicMock
from cronwatcher.alert_manager import Alert
from cronwatcher.job_priority import Priority, PriorityRegistry
from cronwatcher.priority_alert_filter import PriorityAlertFilter


@pytest.fixture
def registry():
    return PriorityRegistry()


@pytest.fixture
def downstream():
    return MagicMock()


@pytest.fixture
def pfilter(registry, downstream):
    f = PriorityAlertFilter(registry=registry, min_priority=Priority.HIGH)
    f.add_handler(downstream)
    return f


def _alert(job_name: str) -> Alert:
    return Alert(kind="missed", job_name=job_name, message="test")


def test_alert_forwarded_when_priority_meets_threshold(registry, pfilter, downstream):
    registry.set_priority("critical_job", Priority.CRITICAL)
    pfilter(_alert("critical_job"))
    downstream.assert_called_once()


def test_alert_forwarded_when_priority_equals_threshold(registry, pfilter, downstream):
    registry.set_priority("high_job", Priority.HIGH)
    pfilter(_alert("high_job"))
    downstream.assert_called_once()


def test_alert_suppressed_when_priority_below_threshold(registry, pfilter, downstream):
    registry.set_priority("low_job", Priority.LOW)
    pfilter(_alert("low_job"))
    downstream.assert_not_called()


def test_default_priority_normal_suppressed_for_high_filter(registry, pfilter, downstream):
    # job not in registry => NORMAL, filter requires HIGH
    pfilter(_alert("unknown_job"))
    downstream.assert_not_called()


def test_configure_changes_threshold(registry, pfilter, downstream):
    pfilter.configure(Priority.LOW)
    registry.set_priority("low_job", Priority.LOW)
    pfilter(_alert("low_job"))
    downstream.assert_called_once()


def test_configure_from_string(registry, pfilter, downstream):
    pfilter.configure("normal")
    # default priority is NORMAL, should now pass
    pfilter(_alert("any_job"))
    downstream.assert_called_once()


def test_multiple_handlers_all_called(registry):
    reg = PriorityRegistry()
    reg.set_priority("job", Priority.CRITICAL)
    h1, h2 = MagicMock(), MagicMock()
    f = PriorityAlertFilter(registry=reg, min_priority=Priority.NORMAL)
    f.add_handler(h1)
    f.add_handler(h2)
    f(_alert("job"))
    h1.assert_called_once()
    h2.assert_called_once()


def test_handle_alias_works(registry, pfilter, downstream):
    registry.set_priority("job", Priority.HIGH)
    pfilter.handle(_alert("job"))
    downstream.assert_called_once()
