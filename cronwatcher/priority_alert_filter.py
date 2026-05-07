"""Alert filter that suppresses alerts for jobs below a minimum priority."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from cronwatcher.alert_manager import Alert
from cronwatcher.job_priority import Priority, PriorityRegistry

Handler = Callable[[Alert], None]


@dataclass
class PriorityAlertFilter:
    """Forwards alerts only when the job's priority meets the minimum threshold."""

    registry: PriorityRegistry
    min_priority: Priority = Priority.NORMAL
    _handlers: List[Handler] = field(default_factory=list, init=False, repr=False)

    def add_handler(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def configure(self, min_priority: Priority | str) -> None:
        """Update the minimum priority threshold at runtime."""
        if isinstance(min_priority, str):
            min_priority = Priority.from_str(min_priority)
        self.min_priority = min_priority

    def __call__(self, alert: Alert) -> None:
        job_priority = self.registry.get_priority(alert.job_name)
        if job_priority >= self.min_priority:
            for handler in self._handlers:
                handler(alert)

    def handle(self, alert: Alert) -> None:
        """Alias for __call__ for consistency with other filter types."""
        self(alert)
