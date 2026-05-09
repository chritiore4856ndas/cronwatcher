"""Alert filter that suppresses alerts for rate-limited jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_ratelimit import RateLimitRegistry


class RateLimitAlertFilter:
    """Forwards alerts only when the job is not currently rate-limited.

    Useful to avoid spamming downstream handlers when a job is intentionally
    being held back by a minimum-interval policy.
    """

    def __init__(self, registry: RateLimitRegistry) -> None:
        self._registry = registry
        self._handlers: List[Callable[[Alert], None]] = []
        self._suppressed: int = 0

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert, now: Optional[datetime] = None) -> None:
        now = now or datetime.utcnow()
        if not self._registry.is_allowed(alert.job_name, now):
            self._suppressed += 1
            return
        for handler in self._handlers:
            handler(alert)

    @property
    def suppressed(self) -> int:
        """Number of alerts suppressed due to rate limiting."""
        return self._suppressed

    def reset_suppressed(self) -> None:
        self._suppressed = 0
