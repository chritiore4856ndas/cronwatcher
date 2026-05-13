"""Blackout periods: suppress all alerts for specific jobs during defined time ranges."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple


@dataclass
class BlackoutPeriod:
    start: time
    end: time
    days: Optional[List[int]] = None  # 0=Monday … 6=Sunday; None means every day

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        if self.days is not None and now.weekday() not in self.days:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current <= self.end
        # overnight window e.g. 23:00 – 02:00
        return current >= self.start or current <= self.end

    def to_dict(self) -> dict:
        return {
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "days": self.days,
        }


class BlackoutRegistry:
    def __init__(self) -> None:
        self._periods: Dict[str, List[BlackoutPeriod]] = {}

    def add(self, job_name: str, period: BlackoutPeriod) -> None:
        self._periods.setdefault(job_name, []).append(period)

    def remove(self, job_name: str) -> None:
        self._periods.pop(job_name, None)

    def is_blacked_out(self, job_name: str, now: Optional[datetime] = None) -> bool:
        for period in self._periods.get(job_name, []):
            if period.is_active(now):
                return True
        return False

    def periods_for(self, job_name: str) -> List[BlackoutPeriod]:
        return list(self._periods.get(job_name, []))

    def all_jobs(self) -> List[str]:
        return list(self._periods.keys())

    def export_all(self) -> Dict[str, list]:
        return {
            job: [p.to_dict() for p in periods]
            for job, periods in self._periods.items()
        }
