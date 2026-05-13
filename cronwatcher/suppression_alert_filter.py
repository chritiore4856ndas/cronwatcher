"""Alert filter that drops alerts for suppressed jobs."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_suppression import SuppressionRegistry


class SuppressionAlertFilter:
    """Wraps downstream alert handlers and silences alerts for suppressed jobs."""

    def __init__(self, registry: SuppressionRegistry) -> None:
        self._registry = registry
        self._handlers: List[Callable[[Alert], None]] = []
        self._suppressed_count: int = 0

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert) -> None:
        if self._registry.is_suppressed(alert.job_name):
            self._suppressed_count += 1
            return
        for handler in self._handlers:
            handler(alert)

    @property
    def suppressed_count(self) -> int:
        return self._suppressed_count

    def reset_suppressed_count(self) -> None:
        self._suppressed_count = 0
