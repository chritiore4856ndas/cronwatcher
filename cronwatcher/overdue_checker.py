"""Checks for overdue (long-running) cron jobs and fires alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cronwatcher.alert_manager import AlertManager
    from cronwatcher.job_tracker import JobTracker


@dataclass
class OverdueChecker:
    """Periodically inspects running jobs and alerts when they exceed their
    expected maximum runtime."""

    tracker: "JobTracker"
    alert_manager: "AlertManager"
    # job_name -> max allowed duration in seconds
    max_runtimes: dict[str, float] = field(default_factory=dict)
    # track which jobs we've already alerted so we don't spam
    _alerted: set[str] = field(default_factory=set, init=False, repr=False)

    def set_max_runtime(self, job_name: str, seconds: float) -> None:
        """Register an expected maximum runtime for a job."""
        if seconds <= 0:
            raise ValueError("max runtime must be positive")
        self.max_runtimes[job_name] = seconds

    def check(self, now=None) -> list[str]:
        """Check all running jobs; return list of job names that are overdue."""
        overdue: list[str] = []
        for name, record in self.tracker.running_jobs(now=now).items():
            limit = self.max_runtimes.get(name)
            if limit is None:
                continue
            dur = record.duration(now=now)
            if dur is not None and dur.total_seconds() > limit:
                overdue.append(name)
                if name not in self._alerted:
                    self._alerted.add(name)
                    self.alert_manager.send(
                        kind="overdue",
                        job_name=name,
                        detail=(
                            f"running for {dur.total_seconds():.1f}s, "
                            f"limit is {limit}s"
                        ),
                    )
        return overdue

    def reset_alerts(self, job_name: str | None = None) -> None:
        """Clear alerted state so the job can trigger a fresh alert next cycle."""
        if job_name is None:
            self._alerted.clear()
        else:
            self._alerted.discard(job_name)
