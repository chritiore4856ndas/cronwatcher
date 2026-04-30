"""Main daemon loop: wires together tracker, checkers, and alert manager."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from cronwatcher.alert_manager import AlertManager
from cronwatcher.config import CronWatcherConfig
from cronwatcher.missed_job_checker import MissedJobChecker
from cronwatcher.overdue_checker import OverdueChecker
from cronwatcher.job_tracker import JobTracker
from cronwatcher.schedule_parser import CronSchedule

log = logging.getLogger(__name__)


@dataclass
class CronWatcherDaemon:
    config: CronWatcherConfig
    alert_manager: AlertManager
    tracker: JobTracker = field(default_factory=JobTracker)
    _missed_checker: MissedJobChecker = field(init=False)
    _overdue_checker: OverdueChecker = field(init=False)

    def __post_init__(self) -> None:
        schedules = {
            j.name: CronSchedule(
                expression=j.schedule,
                grace_seconds=j.grace_seconds,
            )
            for j in self.config.jobs
            if j.enabled
        }
        self._missed_checker = MissedJobChecker(
            schedules=schedules,
            tracker=self.tracker,
            alert_manager=self.alert_manager,
        )
        self._overdue_checker = OverdueChecker(
            tracker=self.tracker,
            alert_manager=self.alert_manager,
        )
        for job in self.config.jobs_with_max_runtime():
            if job.enabled:
                self._overdue_checker.set_max_runtime(
                    job.name, job.max_runtime_seconds
                )

    def run_once(self) -> None:
        """Execute a single check cycle (missed + overdue)."""
        log.debug("Running check cycle")
        self._missed_checker.check()
        self._overdue_checker.check()

    def run(self, *, stop_event=None) -> None:  # pragma: no cover
        """Block and run check cycles until *stop_event* is set (or forever)."""
        log.info(
            "cronwatcher daemon started (interval=%ss)",
            self.config.check_interval_seconds,
        )
        while True:
            self.run_once()
            if stop_event is not None and stop_event.is_set():
                break
            time.sleep(self.config.check_interval_seconds)
        log.info("cronwatcher daemon stopped")
