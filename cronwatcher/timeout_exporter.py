"""Export timeout configuration and current status for monitoring dashboards."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cronwatcher.job_timeout import TimeoutRegistry
from cronwatcher.job_tracker import JobTracker


@dataclass
class TimeoutExporter:
    """Combines registry and live tracker data into serialisable snapshots."""
    registry: TimeoutRegistry
    tracker: JobTracker

    def export_job(self, job_name: str) -> Optional[Dict[str, Any]]:
        """Return timeout info for a single job, or None if no timeout is configured."""
        limit = self.registry.get_timeout(job_name)
        if limit is None:
            return None

        record = self.tracker.get(job_name)
        elapsed: Optional[float] = None
        is_running = False
        exceeded = False

        if record is not None:
            is_running = record.is_running()
            dur = record.duration()
            if dur is not None:
                elapsed = dur.total_seconds()
                exceeded = dur > limit

        return {
            "job_name": job_name,
            "timeout_seconds": limit.total_seconds(),
            "is_running": is_running,
            "elapsed_seconds": elapsed,
            "exceeded": exceeded,
        }

    def export_all(self) -> List[Dict[str, Any]]:
        """Return export snapshots for every job that has a timeout configured."""
        results = []
        for job_name in self.registry.all_jobs():
            entry = self.export_job(job_name)
            if entry is not None:
                results.append(entry)
        return sorted(results, key=lambda x: x["job_name"])

    def jobs_exceeding_timeout(self) -> List[str]:
        """Return names of currently running jobs that have exceeded their timeout."""
        return [
            entry["job_name"]
            for entry in self.export_all()
            if entry["exceeded"] and entry["is_running"]
        ]

    def summary(self) -> Dict[str, Any]:
        """High-level summary suitable for a status endpoint."""
        all_entries = self.export_all()
        exceeded = [e for e in all_entries if e["exceeded"] and e["is_running"]]
        return {
            "total_with_timeout": len(all_entries),
            "currently_exceeding": len(exceeded),
            "jobs_exceeding": [e["job_name"] for e in exceeded],
        }
