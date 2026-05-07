"""Export job priority data for reporting and introspection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from cronwatcher.job_priority import Priority, PriorityRegistry


@dataclass
class PriorityExporter:
    """Provides structured views of the priority registry for dashboards or logs."""

    registry: PriorityRegistry

    def export_job(self, job_name: str) -> Dict[str, Any]:
        """Return a dict describing the priority of a single job."""
        p = self.registry.get_priority(job_name)
        return {
            "job": job_name,
            "priority": p.name,
            "level": int(p),
        }

    def export_all(self) -> List[Dict[str, Any]]:
        """Return a list of priority records for every explicitly registered job."""
        snapshot = self.registry.all_priorities()
        return [
            {
                "job": name,
                "priority": priority_name,
                "level": int(Priority[priority_name]),
            }
            for name, priority_name in sorted(snapshot.items())
        ]

    def jobs_above(self, min_priority: Priority | str) -> List[Dict[str, Any]]:
        """Return export records for jobs whose priority exceeds *min_priority*."""
        names = self.registry.jobs_above(min_priority)
        return [self.export_job(name) for name in sorted(names)]

    def summary(self) -> Dict[str, int]:
        """Return a count of jobs per priority level (only explicitly set jobs)."""
        counts: Dict[str, int] = {p.name: 0 for p in Priority}
        for priority_name in self.registry.all_priorities().values():
            counts[priority_name] += 1
        return counts
