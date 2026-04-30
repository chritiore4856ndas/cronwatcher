"""Simple TOML/dict-based configuration loader for cronwatcher."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str                      # cron expression
    grace_seconds: int = 300           # tolerance before "missed" alert
    max_duration_seconds: int = 3600   # threshold for "overdue" alert
    enabled: bool = True


@dataclass
class LogConfig:
    log_file: Optional[str] = None
    level: str = "WARNING"


@dataclass
class CronWatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    log: LogConfig = field(default_factory=LogConfig)
    check_interval_seconds: int = 60

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CronWatcherConfig":
        jobs = [
            JobConfig(
                name=j["name"],
                schedule=j["schedule"],
                grace_seconds=j.get("grace_seconds", 300),
                max_duration_seconds=j.get("max_duration_seconds", 3600),
                enabled=j.get("enabled", True),
            )
            for j in data.get("jobs", [])
        ]
        raw_log = data.get("log", {})
        log_cfg = LogConfig(
            log_file=raw_log.get("log_file"),
            level=raw_log.get("level", "WARNING"),
        )
        return cls(
            jobs=jobs,
            log=log_cfg,
            check_interval_seconds=data.get("check_interval_seconds", 60),
        )

    @classmethod
    def from_toml(cls, path: str | Path) -> "CronWatcherConfig":
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        return cls.from_dict(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def enabled_jobs(self) -> List[JobConfig]:
        return [j for j in self.jobs if j.enabled]
