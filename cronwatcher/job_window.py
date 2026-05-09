"""Time-window restrictions for cron jobs (e.g. only alert during business hours)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, Optional, Tuple


@dataclass
class WindowEntry:
    """Defines an allowed execution window for a job."""
    start: time   # e.g. time(8, 0)
    end: time     # e.g. time(18, 0)
    days: Tuple[int, ...] = tuple(range(7))  # 0=Mon … 6=Sun, default all days

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if *at* falls inside this window."""
        now = at or datetime.now()
        if now.weekday() not in self.days:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current <= self.end
        # overnight window (e.g. 22:00 – 06:00)
        return current >= self.start or current <= self.end

    def to_dict(self) -> dict:
        return {
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "days": list(self.days),
        }


class WindowRegistry:
    """Stores per-job time-window restrictions."""

    def __init__(self) -> None:
        self._windows: Dict[str, WindowEntry] = {}

    def set_window(self, job_name: str, start: time, end: time,
                   days: Tuple[int, ...] = tuple(range(7))) -> WindowEntry:
        entry = WindowEntry(start=start, end=end, days=days)
        self._windows[job_name] = entry
        return entry

    def get_window(self, job_name: str) -> Optional[WindowEntry]:
        return self._windows.get(job_name)

    def remove_window(self, job_name: str) -> bool:
        return self._windows.pop(job_name, None) is not None

    def is_within_window(self, job_name: str, at: Optional[datetime] = None) -> bool:
        """Return True if the job has no window (unrestricted) or is inside its window."""
        entry = self._windows.get(job_name)
        if entry is None:
            return True
        return entry.is_active(at)

    def all_jobs(self) -> Dict[str, WindowEntry]:
        return dict(self._windows)
