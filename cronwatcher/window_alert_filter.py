"""Alert filter that suppresses alerts for jobs outside their allowed time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_window import WindowRegistry


@dataclass
class WindowAlertFilter:
    """Wraps downstream handlers; drops alerts fired outside a job's window."""

    registry: WindowRegistry
    _handlers: List[Callable[[Alert], None]] = field(default_factory=list, init=False)
    _suppressed: int = field(default=0, init=False)

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert, at: Optional[datetime] = None) -> None:
        if not self.registry.is_within_window(alert.job_name, at):
            self._suppressed += 1
            return
        for handler in self._handlers:
            handler(alert)

    @property
    def suppressed(self) -> int:
        return self._suppressed

    def reset_suppressed(self) -> None:
        self._suppressed = 0
