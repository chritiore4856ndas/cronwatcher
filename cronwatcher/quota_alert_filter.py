"""Alert filter that suppresses alerts for jobs that have exceeded their run quota."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_quota import QuotaRegistry


class QuotaAlertFilter:
    """Forwards alerts only when the job still has quota remaining.

    Jobs with no quota configured are always forwarded.
    """

    def __init__(self, registry: QuotaRegistry) -> None:
        self._registry = registry
        self._handlers: List[Callable[[Alert], None]] = []
        self._suppressed: int = 0

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert) -> None:
        entry = self._registry.get_quota(alert.job_name)
        if entry is not None and not entry.is_allowed():
            self._suppressed += 1
            return
        for handler in self._handlers:
            handler(alert)

    @property
    def suppressed(self) -> int:
        return self._suppressed

    def reset_suppressed(self) -> None:
        self._suppressed = 0
