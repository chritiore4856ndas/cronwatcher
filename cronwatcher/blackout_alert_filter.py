"""Alert filter that drops alerts while a job is in a blackout period."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_blackout import BlackoutRegistry


AlertHandler = Callable[[Alert], None]


class BlackoutAlertFilter:
    """Wraps downstream handlers and suppresses alerts during blackout windows."""

    def __init__(self, registry: BlackoutRegistry) -> None:
        self._registry = registry
        self._handlers: List[AlertHandler] = []
        self._suppressed: int = 0

    def add_handler(self, handler: AlertHandler) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert, now: Optional[datetime] = None) -> None:
        if self._registry.is_blacked_out(alert.job_name, now):
            self._suppressed += 1
            return
        for handler in self._handlers:
            handler(alert)

    @property
    def suppressed_count(self) -> int:
        return self._suppressed

    def reset_suppressed(self) -> None:
        self._suppressed = 0
