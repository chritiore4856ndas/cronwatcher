"""Per-job run quota enforcement: limit how many times a job may run in a given period."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class QuotaEntry:
    job_name: str
    max_runs: int
    period_seconds: float
    _runs: List[datetime] = field(default_factory=list, repr=False)

    def _prune(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.period_seconds)
        self._runs = [t for t in self._runs if t >= cutoff]

    def is_allowed(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        self._prune(now)
        return len(self._runs) < self.max_runs

    def record_run(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.utcnow()
        self._prune(now)
        self._runs.append(now)

    def runs_in_period(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.utcnow()
        self._prune(now)
        return len(self._runs)

    def remaining(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.utcnow()
        self._prune(now)
        return max(0, self.max_runs - len(self._runs))

    def to_dict(self, now: Optional[datetime] = None) -> dict:
        now = now or datetime.utcnow()
        return {
            "job_name": self.job_name,
            "max_runs": self.max_runs,
            "period_seconds": self.period_seconds,
            "runs_in_period": self.runs_in_period(now),
            "remaining": self.remaining(now),
            "allowed": self.is_allowed(now),
        }


class QuotaRegistry:
    def __init__(self) -> None:
        self._entries: Dict[str, QuotaEntry] = {}

    def set_quota(self, job_name: str, max_runs: int, period_seconds: float) -> QuotaEntry:
        entry = QuotaEntry(job_name=job_name, max_runs=max_runs, period_seconds=period_seconds)
        self._entries[job_name] = entry
        return entry

    def get_quota(self, job_name: str) -> Optional[QuotaEntry]:
        return self._entries.get(job_name)

    def remove_quota(self, job_name: str) -> bool:
        return self._entries.pop(job_name, None) is not None

    def all_jobs(self) -> List[str]:
        return list(self._entries.keys())

    def is_allowed(self, job_name: str, now: Optional[datetime] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return True
        return entry.is_allowed(now)

    def record_run(self, job_name: str, now: Optional[datetime] = None) -> None:
        entry = self._entries.get(job_name)
        if entry is not None:
            entry.record_run(now)
