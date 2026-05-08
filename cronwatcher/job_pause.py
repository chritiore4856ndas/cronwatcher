"""Pause/resume support for cron jobs — paused jobs suppress alerts."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PauseEntry:
    job_name: str
    paused_at: float
    reason: str = ""
    resume_at: Optional[float] = None  # None means indefinite

    def is_active(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.time()
        if self.resume_at is None:
            return True
        return t < self.resume_at

    def remaining_seconds(self, now: Optional[float] = None) -> Optional[float]:
        if self.resume_at is None:
            return None
        t = now if now is not None else time.time()
        return max(0.0, self.resume_at - t)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "paused_at": self.paused_at,
            "reason": self.reason,
            "resume_at": self.resume_at,
        }


class PauseRegistry:
    def __init__(self) -> None:
        self._entries: Dict[str, PauseEntry] = {}

    def pause(
        self,
        job_name: str,
        reason: str = "",
        duration_seconds: Optional[float] = None,
        now: Optional[float] = None,
    ) -> PauseEntry:
        t = now if now is not None else time.time()
        resume_at = (t + duration_seconds) if duration_seconds is not None else None
        entry = PauseEntry(job_name=job_name, paused_at=t, reason=reason, resume_at=resume_at)
        self._entries[job_name] = entry
        return entry

    def resume(self, job_name: str) -> bool:
        if job_name in self._entries:
            del self._entries[job_name]
            return True
        return False

    def is_paused(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if entry.is_active(now):
            return True
        # auto-expire
        del self._entries[job_name]
        return False

    def get_entry(self, job_name: str) -> Optional[PauseEntry]:
        return self._entries.get(job_name)

    def all_paused(self, now: Optional[float] = None) -> Dict[str, PauseEntry]:
        expired = [k for k, v in self._entries.items() if not v.is_active(now)]
        for k in expired:
            del self._entries[k]
        return dict(self._entries)

    def reset(self) -> None:
        self._entries.clear()
