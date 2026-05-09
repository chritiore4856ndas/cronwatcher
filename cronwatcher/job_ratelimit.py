"""Rate limiting for cron job executions — prevents jobs from running too frequently."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class RateLimitEntry:
    job_name: str
    min_interval_seconds: float
    last_run: Optional[datetime] = None

    def is_allowed(self, now: Optional[datetime] = None) -> bool:
        """Return True if enough time has passed since the last run."""
        if self.last_run is None:
            return True
        now = now or datetime.utcnow()
        elapsed = (now - self.last_run).total_seconds()
        return elapsed >= self.min_interval_seconds

    def seconds_until_allowed(self, now: Optional[datetime] = None) -> float:
        """Return how many seconds remain before the job is allowed to run again."""
        if self.last_run is None:
            return 0.0
        now = now or datetime.utcnow()
        elapsed = (now - self.last_run).total_seconds()
        remaining = self.min_interval_seconds - elapsed
        return max(0.0, remaining)

    def record_run(self, now: Optional[datetime] = None) -> None:
        """Mark that the job has just run."""
        self.last_run = now or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "min_interval_seconds": self.min_interval_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "seconds_until_allowed": self.seconds_until_allowed(),
        }


class RateLimitRegistry:
    """Registry that tracks per-job rate limits."""

    def __init__(self) -> None:
        self._entries: Dict[str, RateLimitEntry] = {}

    def set_limit(self, job_name: str, min_interval_seconds: float) -> None:
        """Configure a minimum interval between runs for a job."""
        entry = self._entries.get(job_name)
        if entry is None:
            self._entries[job_name] = RateLimitEntry(
                job_name=job_name,
                min_interval_seconds=min_interval_seconds,
            )
        else:
            entry.min_interval_seconds = min_interval_seconds

    def remove_limit(self, job_name: str) -> bool:
        """Remove the rate limit for a job. Returns True if it existed."""
        return self._entries.pop(job_name, None) is not None

    def is_allowed(self, job_name: str, now: Optional[datetime] = None) -> bool:
        """Return True if the job is allowed to run (or has no limit set)."""
        entry = self._entries.get(job_name)
        if entry is None:
            return True
        return entry.is_allowed(now)

    def record_run(self, job_name: str, now: Optional[datetime] = None) -> None:
        """Record that a job has run. No-op if no limit is configured."""
        entry = self._entries.get(job_name)
        if entry is not None:
            entry.record_run(now)

    def get_entry(self, job_name: str) -> Optional[RateLimitEntry]:
        return self._entries.get(job_name)

    def all_jobs(self) -> list[str]:
        return list(self._entries.keys())

    def throttled_jobs(self, now: Optional[datetime] = None) -> list[str]:
        """Return names of jobs currently blocked by their rate limit."""
        now = now or datetime.utcnow()
        return [name for name, e in self._entries.items() if not e.is_allowed(now)]
