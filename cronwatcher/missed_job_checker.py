"""Periodically check registered schedules and fire alerts for missed jobs."""

import logging
from datetime import datetime
from typing import Optional

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_tracker import JobTracker
from cronwatcher.schedule_parser import ScheduleRegistry

logger = logging.getLogger(__name__)


class MissedJobChecker:
    """Cross-references the schedule registry with the job tracker and raises
    alerts for any jobs that appear to have been missed."""

    def __init__(
        self,
        registry: ScheduleRegistry,
        tracker: JobTracker,
        alert_manager: AlertManager,
    ):
        self._registry = registry
        self._tracker = tracker
        self._alert_manager = alert_manager
        # Track which jobs we've already alerted on to avoid spam
        self._alerted: set[str] = set()

    def check(self, now: Optional[datetime] = None) -> list[str]:
        """Run a single check pass. Returns list of job names that were flagged."""
        now = now or datetime.utcnow()
        flagged: list[str] = []

        for schedule in self._registry.all():
            job_name = schedule.job_name
            record = self._tracker.get(job_name)
            last_run: Optional[datetime] = None

            if record is not None and record.finished_at is not None:
                last_run = record.finished_at

            if schedule.is_missed(last_run, now=now):
                alert_key = f"{job_name}:{schedule.last_expected_run(now).isoformat()}"
                if alert_key not in self._alerted:
                    alert = Alert(
                        kind="missed",
                        job_name=job_name,
                        message=(
                            f"Job '{job_name}' missed its scheduled run at "
                            f"{schedule.last_expected_run(now).isoformat()}"
                        ),
                    )
                    self._alert_manager.send(alert)
                    self._alerted.add(alert_key)
                    logger.warning("Missed job detected: %s", job_name)
                flagged.append(job_name)

        return flagged

    def reset_alerts(self, job_name: str) -> None:
        """Clear alert state for a job (e.g. after it successfully runs)."""
        self._alerted = {
            k for k in self._alerted if not k.startswith(f"{job_name}:")
        }
