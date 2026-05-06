"""Persistent job run history with a rolling window."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional


@dataclass
class RunEntry:
    job_name: str
    started_at: float
    finished_at: Optional[float] = None
    exit_ok: bool = True

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return self.finished_at - self.started_at

    def to_dict(self) -> dict:
        return {
            "job": self.job_name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration": self.duration,
            "exit_ok": self.exit_ok,
        }


class JobHistory:
    """Keeps the last *maxlen* run entries per job in memory."""

    def __init__(self, maxlen: int = 100) -> None:
        self._maxlen = maxlen
        self._runs: Dict[str, Deque[RunEntry]] = {}

    # ------------------------------------------------------------------
    def record_start(self, job_name: str, started_at: Optional[float] = None) -> RunEntry:
        entry = RunEntry(
            job_name=job_name,
            started_at=started_at if started_at is not None else time.time(),
        )
        self._runs.setdefault(job_name, deque(maxlen=self._maxlen)).append(entry)
        return entry

    def record_finish(
        self,
        job_name: str,
        exit_ok: bool = True,
        finished_at: Optional[float] = None,
    ) -> Optional[RunEntry]:
        entries = self._runs.get(job_name)
        if not entries:
            return None
        entry = entries[-1]
        entry.finished_at = finished_at if finished_at is not None else time.time()
        entry.exit_ok = exit_ok
        return entry

    # ------------------------------------------------------------------
    def get(self, job_name: str) -> List[RunEntry]:
        return list(self._runs.get(job_name, []))

    def last(self, job_name: str) -> Optional[RunEntry]:
        entries = self._runs.get(job_name)
        return entries[-1] if entries else None

    def all_jobs(self) -> List[str]:
        return list(self._runs.keys())

    def failure_rate(self, job_name: str) -> float:
        entries = self._runs.get(job_name)
        if not entries:
            return 0.0
        failed = sum(1 for e in entries if not e.exit_ok)
        return failed / len(entries)

    def clear(self, job_name: str) -> None:
        self._runs.pop(job_name, None)
