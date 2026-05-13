"""Tests for FlapDetector."""

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_flap_detector import FlapDetector, FlapState


@pytest.fixture
def alert_manager():
    am = AlertManager()
    am.send = MagicMock()
    return am


@pytest.fixture
def detector(alert_manager):
    # small window/threshold for easy testing
    return FlapDetector(alert_manager, window=4, threshold=3)


def _alternate(detector: FlapDetector, job: str, count: int) -> None:
    """Record alternating success/failure pairs."""
    for i in range(count):
        if i % 2 == 0:
            detector.record_failure(job)
        else:
            detector.record_success(job)


def test_no_alert_on_single_outcome(detector, alert_manager):
    detector.record_success("backup")
    alert_manager.send.assert_not_called()


def test_no_alert_below_threshold(detector, alert_manager):
    # 2 alternations, threshold is 3
    detector.record_success("backup")
    detector.record_failure("backup")
    detector.record_success("backup")
    alert_manager.send.assert_not_called()


def test_alert_fires_when_flapping(detector, alert_manager):
    _alternate(detector, "backup", 4)  # 3 alternations within window of 4
    alert_manager.send.assert_called_once()
    alert: Alert = alert_manager.send.call_args[0][0]
    assert alert.kind == "flapping"
    assert alert.job_name == "backup"
    assert "flapping" in alert.message


def test_alert_fires_only_once_while_flapping(detector, alert_manager):
    _alternate(detector, "backup", 4)
    _alternate(detector, "backup", 2)  # still flapping
    assert alert_manager.send.call_count == 1


def test_alert_resets_after_stable_run(detector, alert_manager):
    _alternate(detector, "backup", 4)  # triggers alert
    # now record consistent successes to push alternations out of window
    for _ in range(4):
        detector.record_success("backup")
    # should no longer be flapping; next flap should trigger again
    _alternate(detector, "backup", 4)
    assert alert_manager.send.call_count == 2


def test_alternation_count_correct():
    state = FlapState(job_name="x", window=6, threshold=4)
    for v in [True, False, True, False]:
        state.record(v)
    assert state.alternation_count() == 3


def test_is_flapping_false_with_one_entry():
    state = FlapState(job_name="x", window=6, threshold=4)
    state.record(True)
    assert not state.is_flapping()


def test_reset_removes_state(detector):
    detector.record_success("job1")
    detector.reset("job1")
    assert detector.state_for("job1") is None


def test_multiple_jobs_tracked_independently(detector, alert_manager):
    _alternate(detector, "job_a", 4)
    detector.record_success("job_b")
    detector.record_success("job_b")
    # only job_a should have triggered an alert
    assert alert_manager.send.call_count == 1
    assert alert_manager.send.call_args[0][0].job_name == "job_a"


def test_state_for_unknown_job_returns_none(detector):
    assert detector.state_for("ghost") is None
