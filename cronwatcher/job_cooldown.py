"""Tracks per-job cooldown periods to suppress rapid re-alerting after a job recovers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class CooldownEntry:
    job_name: str
    started_at: datetime
    duration_seconds: float

    def expires_at(self) -> datetime:
        return self.started_at + timedelta(seconds=self.duration_seconds)

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        return now < self.expires_at()

    def remaining_seconds(self, now: Optional[datetime] = None) -> float:
        now = now or datetime.utcnow()
        remaining = (self.expires_at() - now).total_seconds()
        return max(0.0, remaining)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "expires_at": self.expires_at().isoformat(),
        }


class JobCooldown:
    """Manages cooldown windows for jobs after alerts are resolved."""

    def __init__(self, default_seconds: float = 300.0) -> None:
        self.default_seconds = default_seconds
        self._entries: Dict[str, CooldownEntry] = {}
        self._overrides: Dict[str, float] = {}

    def set_override(self, job_name: str, seconds: float) -> None:
        """Override the cooldown duration for a specific job."""
        self._overrides[job_name] = seconds

    def start(self, job_name: str, now: Optional[datetime] = None) -> CooldownEntry:
        """Begin a cooldown window for the given job."""
        now = now or datetime.utcnow()
        duration = self._overrides.get(job_name, self.default_seconds)
        entry = CooldownEntry(job_name=job_name, started_at=now, duration_seconds=duration)
        self._entries[job_name] = entry
        return entry

    def is_cooling(self, job_name: str, now: Optional[datetime] = None) -> bool:
        """Return True if the job is currently within its cooldown window."""
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        return entry.is_active(now)

    def clear(self, job_name: str) -> None:
        """Remove any active cooldown for the given job."""
        self._entries.pop(job_name, None)

    def clear_all(self) -> None:
        self._entries.clear()

    def get_entry(self, job_name: str) -> Optional[CooldownEntry]:
        return self._entries.get(job_name)

    def active_jobs(self, now: Optional[datetime] = None) -> Dict[str, CooldownEntry]:
        now = now or datetime.utcnow()
        return {name: e for name, e in self._entries.items() if e.is_active(now)}
