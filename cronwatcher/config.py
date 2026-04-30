"""Configuration dataclasses and loaders for cronwatcher."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class JobConfig:
    name: str
    schedule: str
    grace_seconds: float = 60.0
    max_runtime_seconds: float | None = None
    enabled: bool = True


@dataclass
class LogConfig:
    level: str = "INFO"
    file: str | None = None


@dataclass
class CronWatcherConfig:
    jobs: list[JobConfig] = field(default_factory=list)
    log: LogConfig = field(default_factory=LogConfig)
    check_interval_seconds: float = 30.0

    # ------------------------------------------------------------------ #
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CronWatcherConfig":
        jobs = [
            JobConfig(
                name=j["name"],
                schedule=j["schedule"],
                grace_seconds=float(j.get("grace_seconds", 60)),
                max_runtime_seconds=(
                    float(j["max_runtime_seconds"])
                    if "max_runtime_seconds" in j
                    else None
                ),
                enabled=bool(j.get("enabled", True)),
            )
            for j in data.get("jobs", [])
        ]
        raw_log = data.get("log", {})
        log = LogConfig(
            level=raw_log.get("level", "INFO"),
            file=raw_log.get("file"),
        )
        return cls(
            jobs=jobs,
            log=log,
            check_interval_seconds=float(
                data.get("check_interval_seconds", 30)
            ),
        )

    @classmethod
    def from_toml(cls, path: str | Path) -> "CronWatcherConfig":
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        return cls.from_dict(data)

    def jobs_with_max_runtime(self) -> list[JobConfig]:
        """Return only jobs that have a max_runtime_seconds configured."""
        return [j for j in self.jobs if j.max_runtime_seconds is not None]
