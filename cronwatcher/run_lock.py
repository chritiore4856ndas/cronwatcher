"""Tracks whether a job is currently locked (i.e. already running) to prevent duplicate alerts."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LockEntry:
    job_name: str
    acquired_at: float = field(default_factory=time.monotonic)
    owner_pid: Optional[int] = None

    @property
    def held_for(self) -> float:
        """Seconds since the lock was acquired."""
        return time.monotonic() - self.acquired_at

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "acquired_at": self.acquired_at,
            "held_for": round(self.held_for, 3),
            "owner_pid": self.owner_pid,
        }


class RunLock:
    """In-memory lock registry that prevents duplicate concurrent runs from being tracked."""

    def __init__(self) -> None:
        self._locks: Dict[str, LockEntry] = {}

    def acquire(self, job_name: str, owner_pid: Optional[int] = None) -> bool:
        """Try to acquire a lock for *job_name*. Returns True if successful, False if already locked."""
        if job_name in self._locks:
            return False
        self._locks[job_name] = LockEntry(job_name=job_name, owner_pid=owner_pid)
        return True

    def release(self, job_name: str) -> bool:
        """Release the lock for *job_name*. Returns True if a lock existed."""
        return self._locks.pop(job_name, None) is not None

    def is_locked(self, job_name: str) -> bool:
        return job_name in self._locks

    def get(self, job_name: str) -> Optional[LockEntry]:
        return self._locks.get(job_name)

    def all_locks(self) -> Dict[str, LockEntry]:
        return dict(self._locks)

    def release_all(self) -> None:
        self._locks.clear()
