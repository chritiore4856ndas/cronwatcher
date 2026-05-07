"""Tests for cronwatcher.job_cooldown."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.job_cooldown import CooldownEntry, JobCooldown


@pytest.fixture
def cooldown() -> JobCooldown:
    return JobCooldown(default_seconds=60.0)


def _t(offset_seconds: float = 0.0) -> datetime:
    base = datetime(2024, 6, 1, 12, 0, 0)
    return base + timedelta(seconds=offset_seconds)


def test_entry_is_active_before_expiry():
    entry = CooldownEntry(job_name="backup", started_at=_t(0), duration_seconds=60)
    assert entry.is_active(now=_t(30)) is True


def test_entry_is_inactive_after_expiry():
    entry = CooldownEntry(job_name="backup", started_at=_t(0), duration_seconds=60)
    assert entry.is_active(now=_t(61)) is False


def test_remaining_seconds_decreases():
    entry = CooldownEntry(job_name="backup", started_at=_t(0), duration_seconds=60)
    assert entry.remaining_seconds(now=_t(40)) == pytest.approx(20.0)


def test_remaining_seconds_floored_at_zero():
    entry = CooldownEntry(job_name="backup", started_at=_t(0), duration_seconds=60)
    assert entry.remaining_seconds(now=_t(120)) == 0.0


def test_to_dict_has_expected_keys():
    entry = CooldownEntry(job_name="sync", started_at=_t(0), duration_seconds=30)
    d = entry.to_dict()
    assert set(d.keys()) == {"job_name", "started_at", "duration_seconds", "expires_at"}


def test_start_creates_active_entry(cooldown):
    entry = cooldown.start("nightly", now=_t(0))
    assert cooldown.is_cooling("nightly", now=_t(30)) is True
    assert entry.job_name == "nightly"


def test_not_cooling_before_start(cooldown):
    assert cooldown.is_cooling("unknown") is False


def test_not_cooling_after_expiry(cooldown):
    cooldown.start("nightly", now=_t(0))
    assert cooldown.is_cooling("nightly", now=_t(61)) is False


def test_clear_removes_entry(cooldown):
    cooldown.start("nightly", now=_t(0))
    cooldown.clear("nightly")
    assert cooldown.is_cooling("nightly", now=_t(10)) is False


def test_clear_nonexistent_does_not_raise(cooldown):
    cooldown.clear("ghost")  # should not raise


def test_override_changes_duration(cooldown):
    cooldown.set_override("fast_job", 10.0)
    cooldown.start("fast_job", now=_t(0))
    assert cooldown.is_cooling("fast_job", now=_t(5)) is True
    assert cooldown.is_cooling("fast_job", now=_t(11)) is False


def test_active_jobs_returns_only_active(cooldown):
    cooldown.start("job_a", now=_t(0))
    cooldown.start("job_b", now=_t(0))
    # expire job_b by using a very short duration
    cooldown.set_override("job_c", 5.0)
    cooldown.start("job_c", now=_t(0))

    active = cooldown.active_jobs(now=_t(6))
    assert "job_a" in active
    assert "job_b" in active
    assert "job_c" not in active


def test_clear_all_removes_all_entries(cooldown):
    cooldown.start("job_a", now=_t(0))
    cooldown.start("job_b", now=_t(0))
    cooldown.clear_all()
    assert cooldown.active_jobs(now=_t(1)) == {}


def test_get_entry_returns_none_for_unknown(cooldown):
    assert cooldown.get_entry("missing") is None


def test_get_entry_returns_entry_after_start(cooldown):
    cooldown.start("known", now=_t(0))
    entry = cooldown.get_entry("known")
    assert entry is not None
    assert entry.job_name == "known"
