"""Tests for cronwatcher.job_escalation."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_escalation import EscalationLevel, EscalationPolicy, EscalationState


@pytest.fixture()
def alert_manager():
    mgr = AlertManager()
    mgr._sent: list[Alert] = []
    mgr.register_handler(lambda a: mgr._sent.append(a))
    return mgr


@pytest.fixture()
def policy(alert_manager):
    levels = [
        EscalationLevel(threshold=2, kind="warn_missed", message_suffix="Please check."),
        EscalationLevel(threshold=5, kind="critical_missed", message_suffix="Immediate action required."),
    ]
    return EscalationPolicy(alert_manager, levels)


def test_single_miss_below_threshold_fires_no_alert(policy, alert_manager):
    policy.record_miss("backup")
    assert alert_manager._sent == []


def test_second_miss_fires_warn_alert(policy, alert_manager):
    policy.record_miss("backup")
    policy.record_miss("backup")
    assert len(alert_manager._sent) == 1
    assert alert_manager._sent[0].kind == "warn_missed"
    assert "backup" in alert_manager._sent[0].message


def test_warn_level_fires_only_once(policy, alert_manager):
    for _ in range(4):
        policy.record_miss("backup")
    warn_alerts = [a for a in alert_manager._sent if a.kind == "warn_missed"]
    assert len(warn_alerts) == 1


def test_fifth_miss_fires_critical_alert(policy, alert_manager):
    for _ in range(5):
        policy.record_miss("backup")
    kinds = [a.kind for a in alert_manager._sent]
    assert "critical_missed" in kinds


def test_message_contains_suffix(policy, alert_manager):
    policy.record_miss("backup")
    policy.record_miss("backup")
    assert "Please check." in alert_manager._sent[0].message


def test_success_resets_state(policy, alert_manager):
    policy.record_miss("backup")
    policy.record_miss("backup")
    policy.record_success("backup")
    state = policy.state_for("backup")
    assert state.miss_count == 0
    assert state.levels_fired == []


def test_after_reset_escalation_restarts(policy, alert_manager):
    for _ in range(2):
        policy.record_miss("backup")
    policy.record_success("backup")
    alert_manager._sent.clear()
    for _ in range(2):
        policy.record_miss("backup")
    assert len(alert_manager._sent) == 1
    assert alert_manager._sent[0].kind == "warn_missed"


def test_state_for_unknown_job_returns_none(policy):
    assert policy.state_for("nonexistent") is None


def test_multiple_jobs_tracked_independently(policy, alert_manager):
    policy.record_miss("job_a")
    policy.record_miss("job_a")
    policy.record_miss("job_b")
    warn_alerts = [a for a in alert_manager._sent if a.kind == "warn_missed"]
    assert len(warn_alerts) == 1
    assert warn_alerts[0].job_name == "job_a"


def test_add_level_dynamically(alert_manager):
    p = EscalationPolicy(alert_manager)
    p.add_level(EscalationLevel(threshold=1, kind="immediate"))
    p.record_miss("db_dump")
    assert len(alert_manager._sent) == 1
    assert alert_manager._sent[0].kind == "immediate"


def test_all_states_returns_all_tracked_jobs(policy):
    policy.record_miss("job_x")
    policy.record_miss("job_y")
    states = policy.all_states()
    assert "job_x" in states
    assert "job_y" in states
