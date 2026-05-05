"""Hooks MetricsCollector into alert events and job tracker completions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_tracker import JobTracker
from cronwatcher.metrics import MetricsCollector

if TYPE_CHECKING:
    pass


@dataclass
class MetricsReporter:
    """Wires alert events and finished jobs into MetricsCollector."""

    tracker: JobTracker
    alert_manager: AlertManager
    collector: MetricsCollector = field(default_factory=MetricsCollector)

    def __post_init__(self) -> None:
        self.alert_manager.register_handler(self._on_alert)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def record_finished(self, job_name: str) -> None:
        """Call after a job finishes to capture its duration."""
        record = self.tracker.get(job_name)
        if record is None or record.is_running:
            return
        if record.duration is not None:
            self.collector.record_run(job_name, record.duration)

    def summary(self) -> list[dict]:
        """Return metrics for all tracked jobs."""
        return self.collector.all()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_alert(self, alert: Alert) -> None:
        if alert.kind == "missed":
            self.collector.record_miss(alert.job_name)
        elif alert.kind == "overdue":
            self.collector.record_overdue(alert.job_name)
