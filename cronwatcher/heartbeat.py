"""Heartbeat tracker — detects jobs that started but never finished."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_tracker import JobTracker


@dataclass
class HeartbeatMonitor:
    """Periodically checks for jobs that appear to be stuck (started, never finished)."""

    tracker: JobTracker
    alert_manager: AlertManager
    # How long a job can be running before we consider it a zombie
    zombie_threshold: timedelta = field(default_factory=lambda: timedelta(hours=1))

    # Track which jobs we've already alerted on so we don't spam
    _alerted: Dict[str, datetime] = field(default_factory=dict, init=False)

    def check(self, now: Optional[datetime] = None) -> None:
        """Scan all running jobs and alert on any that exceed the zombie threshold."""
        now = now or datetime.utcnow()

        for job_name, record in self.tracker.all_records().items():
            if not record.is_running():
                # Job finished cleanly — clear any previous alert state
                self._alerted.pop(job_name, None)
                continue

            duration = record.duration(now)
            if duration is None:
                continue

            if duration >= self.zombie_threshold:
                if job_name not in self._alerted:
                    alert = Alert(
                        kind="zombie",
                        job_name=job_name,
                        message=(
                            f"Job '{job_name}' has been running for "
                            f"{int(duration.total_seconds())}s with no finish signal."
                        ),
                        timestamp=now,
                    )
                    self.alert_manager.send(alert)
                    self._alerted[job_name] = now

    def reset_alerts(self) -> None:
        """Clear the alerted set (useful for testing or after an ack)."""
        self._alerted.clear()
