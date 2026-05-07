"""Per-job timeout registry and checker that fires alerts when jobs exceed their time limits."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, Optional

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_tracker import JobTracker


@dataclass
class TimeoutRegistry:
    """Stores per-job timeout limits."""
    _limits: Dict[str, timedelta] = field(default_factory=dict)

    def set_timeout(self, job_name: str, seconds: float) -> None:
        """Register a timeout in seconds for a job."""
        if seconds <= 0:
            raise ValueError(f"Timeout must be positive, got {seconds}")
        self._limits[job_name] = timedelta(seconds=seconds)

    def get_timeout(self, job_name: str) -> Optional[timedelta]:
        """Return the timeout for a job, or None if not set."""
        return self._limits.get(job_name)

    def remove_timeout(self, job_name: str) -> None:
        """Remove the timeout for a job."""
        self._limits.pop(job_name, None)

    def all_jobs(self) -> Dict[str, timedelta]:
        """Return a copy of all registered timeouts."""
        return dict(self._limits)


@dataclass
class JobTimeoutChecker:
    """Checks running jobs against their registered timeouts and fires alerts."""
    registry: TimeoutRegistry
    tracker: JobTracker
    alert_manager: AlertManager
    _alerted: Dict[str, bool] = field(default_factory=dict)

    def check(self) -> None:
        """Inspect all running jobs; alert once per job that exceeds its timeout."""
        for job_name, limit in self.registry.all_jobs().items():
            record = self.tracker.get(job_name)
            if record is None or not record.is_running():
                # Job finished or not started — clear any previous alert state
                self._alerted.pop(job_name, None)
                continue

            if self._alerted.get(job_name):
                continue

            elapsed = record.duration()
            if elapsed is not None and elapsed > limit:
                alert = Alert(
                    kind="timeout",
                    job_name=job_name,
                    message=(
                        f"Job '{job_name}' exceeded timeout of {limit.total_seconds():.0f}s "
                        f"(running for {elapsed.total_seconds():.1f}s)"
                    ),
                )
                self.alert_manager.send(alert)
                self._alerted[job_name] = True

    def reset_alerts(self, job_name: str) -> None:
        """Clear the alerted flag for a specific job (e.g. after it finishes)."""
        self._alerted.pop(job_name, None)
