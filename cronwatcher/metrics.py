"""Simple in-memory metrics collector for cronwatcher."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class JobMetrics:
    job_name: str
    run_count: int = 0
    miss_count: int = 0
    overdue_count: int = 0
    durations: List[float] = field(default_factory=list)

    @property
    def avg_duration(self) -> float | None:
        if not self.durations:
            return None
        return sum(self.durations) / len(self.durations)

    @property
    def max_duration(self) -> float | None:
        return max(self.durations) if self.durations else None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "run_count": self.run_count,
            "miss_count": self.miss_count,
            "overdue_count": self.overdue_count,
            "avg_duration_seconds": self.avg_duration,
            "max_duration_seconds": self.max_duration,
        }


class MetricsCollector:
    """Collects and exposes per-job runtime metrics."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobMetrics] = defaultdict(
            lambda: JobMetrics(job_name="")
        )

    def _get(self, job_name: str) -> JobMetrics:
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetrics(job_name=job_name)
        return self._jobs[job_name]

    def record_run(self, job_name: str, duration: float) -> None:
        m = self._get(job_name)
        m.run_count += 1
        m.durations.append(duration)

    def record_miss(self, job_name: str) -> None:
        self._get(job_name).miss_count += 1

    def record_overdue(self, job_name: str) -> None:
        self._get(job_name).overdue_count += 1

    def get(self, job_name: str) -> JobMetrics | None:
        return self._jobs.get(job_name)

    def all(self) -> List[dict]:
        return [m.to_dict() for m in self._jobs.values()]

    def reset(self, job_name: str | None = None) -> None:
        if job_name is not None:
            self._jobs.pop(job_name, None)
        else:
            self._jobs.clear()
