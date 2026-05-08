"""Export pause state for reporting and status endpoints."""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from cronwatcher.job_pause import PauseEntry, PauseRegistry


class PauseExporter:
    def __init__(self, registry: PauseRegistry) -> None:
        self._registry = registry

    def export_job(self, job_name: str, now: Optional[float] = None) -> Optional[dict]:
        entry = self._registry.get_entry(job_name)
        if entry is None:
            return None
        t = now if now is not None else time.time()
        if not entry.is_active(t):
            return None
        d = entry.to_dict()
        d["remaining_seconds"] = entry.remaining_seconds(t)
        return d

    def export_all(self, now: Optional[float] = None) -> Dict[str, dict]:
        t = now if now is not None else time.time()
        result = {}
        for job_name, entry in self._registry.all_paused(t).items():
            d = entry.to_dict()
            d["remaining_seconds"] = entry.remaining_seconds(t)
            result[job_name] = d
        return result

    def paused_job_names(self, now: Optional[float] = None) -> List[str]:
        t = now if now is not None else time.time()
        return list(self._registry.all_paused(t).keys())

    def summary(self, now: Optional[float] = None) -> dict:
        t = now if now is not None else time.time()
        paused = self._registry.all_paused(t)
        indefinite = [k for k, v in paused.items() if v.resume_at is None]
        timed = [k for k, v in paused.items() if v.resume_at is not None]
        return {
            "total_paused": len(paused),
            "indefinite": indefinite,
            "timed": timed,
        }
