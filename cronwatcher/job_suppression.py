"""Suppression registry — temporarily silence alerts for specific jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SuppressionEntry:
    job_name: str
    reason: str
    suppressed_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None  # None means indefinite

    def is_active(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        if self.expires_at is None:
            return True
        return now < self.expires_at

    def remaining_seconds(self, now: Optional[float] = None) -> Optional[float]:
        if self.expires_at is None:
            return None
        if now is None:
            now = time.time()
        return max(0.0, self.expires_at - now)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "reason": self.reason,
            "suppressed_at": self.suppressed_at,
            "expires_at": self.expires_at,
            "active": self.is_active(),
        }


class SuppressionRegistry:
    def __init__(self) -> None:
        self._entries: Dict[str, SuppressionEntry] = {}

    def suppress(self, job_name: str, reason: str, duration_seconds: Optional[float] = None) -> SuppressionEntry:
        """Suppress alerts for *job_name*. Pass duration_seconds=None for indefinite."""
        now = time.time()
        expires_at = (now + duration_seconds) if duration_seconds is not None else None
        entry = SuppressionEntry(
            job_name=job_name,
            reason=reason,
            suppressed_at=now,
            expires_at=expires_at,
        )
        self._entries[job_name] = entry
        return entry

    def lift(self, job_name: str) -> bool:
        """Remove suppression for *job_name*. Returns True if an entry existed."""
        return self._entries.pop(job_name, None) is not None

    def is_suppressed(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if not entry.is_active(now):
            # auto-expire
            del self._entries[job_name]
            return False
        return True

    def get(self, job_name: str) -> Optional[SuppressionEntry]:
        return self._entries.get(job_name)

    def all_suppressed(self, now: Optional[float] = None) -> Dict[str, SuppressionEntry]:
        """Return only currently-active entries, pruning expired ones."""
        active = {k: v for k, v in self._entries.items() if v.is_active(now)}
        self._entries = active
        return dict(active)

    def reset(self) -> None:
        self._entries.clear()
