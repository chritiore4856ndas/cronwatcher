"""Alert filter that suppresses alerts for paused jobs."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_pause import PauseRegistry


class PauseAlertFilter:
    """Wraps downstream alert handlers and drops alerts for paused jobs."""

    def __init__(self, registry: PauseRegistry) -> None:
        self._registry = registry
        self._handlers: List[Callable[[Alert], None]] = []
        self._suppressed: List[Alert] = []

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert) -> None:
        if self._registry.is_paused(alert.job_name):
            self._suppressed.append(alert)
            return
        for h in self._handlers:
            h(alert)

    @property
    def suppressed(self) -> List[Alert]:
        return list(self._suppressed)

    def suppressed_count(self, job_name: Optional[str] = None) -> int:
        if job_name is None:
            return len(self._suppressed)
        return sum(1 for a in self._suppressed if a.job_name == job_name)

    def clear_suppressed(self) -> None:
        self._suppressed.clear()
