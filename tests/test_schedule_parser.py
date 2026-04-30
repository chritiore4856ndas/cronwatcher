"""Tests for schedule_parser and MissedJobChecker."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.schedule_parser import CronSchedule, ScheduleRegistry


# ---------------------------------------------------------------------------
# CronSchedule
# ---------------------------------------------------------------------------

def test_invalid_expression_raises():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        CronSchedule(job_name="bad", expression="not a cron")


def test_last_expected_run_is_in_the_past():
    schedule = CronSchedule(job_name="hourly", expression="0 * * * *")
    now = datetime(2024, 6, 1, 14, 30, 0)
    last = schedule.last_expected_run(now)
    assert last < now
    assert last.minute == 0
    assert last.hour == 14


def test_next_expected_run_is_in_the_future():
    schedule = CronSchedule(job_name="hourly", expression="0 * * * *")
    now = datetime(2024, 6, 1, 14, 30, 0)
    nxt = schedule.next_expected_run(now)
    assert nxt > now
    assert nxt.hour == 15


def test_is_missed_when_no_last_run_and_grace_passed():
    schedule = CronSchedule(
        job_name="test", expression="0 * * * *", grace_period_seconds=60
    )
    # Simulate being 2 minutes past the top of the hour
    now = datetime(2024, 6, 1, 14, 2, 0)
    assert schedule.is_missed(last_run=None, now=now) is True


def test_not_missed_within_grace_period():
    schedule = CronSchedule(
        job_name="test", expression="0 * * * *", grace_period_seconds=300
    )
    now = datetime(2024, 6, 1, 14, 1, 0)  # only 1 min past, grace is 5 min
    assert schedule.is_missed(last_run=None, now=now) is False


def test_not_missed_when_ran_after_last_expected():
    schedule = CronSchedule(
        job_name="test", expression="0 * * * *", grace_period_seconds=60
    )
    now = datetime(2024, 6, 1, 14, 5, 0)
    last_run = datetime(2024, 6, 1, 14, 0, 30)  # ran just after the hour
    assert schedule.is_missed(last_run=last_run, now=now) is False


def test_missed_when_last_run_is_stale():
    schedule = CronSchedule(
        job_name="test", expression="0 * * * *", grace_period_seconds=60
    )
    now = datetime(2024, 6, 1, 14, 5, 0)
    last_run = datetime(2024, 6, 1, 13, 0, 30)  # ran an hour ago
    assert schedule.is_missed(last_run=last_run, now=now) is True


# ---------------------------------------------------------------------------
# ScheduleRegistry
# ---------------------------------------------------------------------------

def test_registry_register_and_get():
    reg = ScheduleRegistry()
    s = CronSchedule(job_name="backup", expression="0 2 * * *")
    reg.register(s)
    assert reg.get("backup") is s
    assert len(reg) == 1


def test_registry_get_unknown_returns_none():
    reg = ScheduleRegistry()
    assert reg.get("nonexistent") is None


def test_registry_all_returns_all_schedules():
    reg = ScheduleRegistry()
    reg.register(CronSchedule(job_name="a", expression="* * * * *"))
    reg.register(CronSchedule(job_name="b", expression="0 * * * *"))
    names = {s.job_name for s in reg.all()}
    assert names == {"a", "b"}
