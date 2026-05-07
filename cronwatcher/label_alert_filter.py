"""Alert handler that forwards alerts only for jobs matching a label selector."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_labels import LabelRegistry

AlertHandler = Callable[[Alert], None]


@dataclass
class LabelAlertFilter:
    """Wraps a downstream handler and only forwards alerts whose job matches a label selector.

    If *selector* is empty all alerts pass through (no-op filter).
    """

    registry: LabelRegistry
    downstream: AlertHandler
    selector: Dict[str, str] = field(default_factory=dict)

    def configure(self, selector: Dict[str, str]) -> None:
        """Update the label selector used for filtering."""
        self.selector = dict(selector)

    def __call__(self, alert: Alert) -> None:
        """Forward *alert* to downstream if the job matches the current selector."""
        if not self.selector:
            self.downstream(alert)
            return

        matched = self.registry.jobs_matching_all(self.selector)
        if alert.job_name in matched:
            self.downstream(alert)

    # Allow use as a named handler registered with AlertManager
    handle = __call__
