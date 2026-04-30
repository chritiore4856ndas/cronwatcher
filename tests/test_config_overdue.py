"""Tests that verify config correctly surfaces overdue-related settings."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronwatcher.config import CronWatcherConfig, JobConfig


def test_from_dict_parses_max_runtime():
    data = {
        "jobs": [
            {"name": "backup", "schedule": "0 2 * * *", "max_runtime_seconds": 120},
            {"name": "report", "schedule": "0 6 * * *"},
        ]
    }
    cfg = CronWatcherConfig.from_dict(data)

    assert cfg.jobs[0].max_runtime_seconds == 120.0
    assert cfg.jobs[1].max_runtime_seconds is None


def test_jobs_with_max_runtime_filters_correctly():
    data = {
        "jobs": [
            {"name": "a", "schedule": "* * * * *", "max_runtime_seconds": 30},
            {"name": "b", "schedule": "* * * * *"},
            {"name": "c", "schedule": "* * * * *", "max_runtime_seconds": 90},
        ]
    }
    cfg = CronWatcherConfig.from_dict(data)
    limited = cfg.jobs_with_max_runtime()

    assert [j.name for j in limited] == ["a", "c"]


def test_from_toml_parses_max_runtime(tmp_path: Path):
    toml_file = tmp_path / "cronwatcher.toml"
    toml_file.write_text(
        textwrap.dedent(
            """
            check_interval_seconds = 15

            [[jobs]]
            name = "nightly"
            schedule = "0 3 * * *"
            max_runtime_seconds = 300
            grace_seconds = 120

            [[jobs]]
            name = "hourly"
            schedule = "0 * * * *"
            """
        )
    )
    cfg = CronWatcherConfig.from_toml(toml_file)

    assert cfg.check_interval_seconds == 15.0
    nightly = next(j for j in cfg.jobs if j.name == "nightly")
    assert nightly.max_runtime_seconds == 300.0
    assert nightly.grace_seconds == 120.0

    hourly = next(j for j in cfg.jobs if j.name == "hourly")
    assert hourly.max_runtime_seconds is None


def test_no_jobs_with_max_runtime_returns_empty():
    data = {"jobs": [{"name": "x", "schedule": "* * * * *"}]}
    cfg = CronWatcherConfig.from_dict(data)
    assert cfg.jobs_with_max_runtime() == []
