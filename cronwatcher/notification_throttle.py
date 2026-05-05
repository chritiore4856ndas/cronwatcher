"""Throttle repeated alerts for the same job to avoid notification spam."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


@dataclass
class NotificationThrottle:
    """Suppresses duplicate alerts for the same job+kind within a cooldown window."""

    cooldown_seconds: int = 300  # 5 minutes default
    _last_sent: Dict[Tuple[str, str], datetime] = field(default_factory=dict, init=False)
    _suppressed_count: Dict[Tuple[str, str], int] = field(default_factory=dict, init=False)

    def should_send(self, job_name: str, kind: str, now: Optional[datetime] = None) -> bool:
        """Return True if the alert should be sent, False if it should be suppressed."""
        if now is None:
            now = datetime.utcnow()

        key = (job_name, kind)
        last = self._last_sent.get(key)

        if last is None:
            self._last_sent[key] = now
            return True

        elapsed = (now - last).total_seconds()
        if elapsed >= self.cooldown_seconds:
            self._last_sent[key] = now
            self._suppressed_count.pop(key, None)
            return True

        self._suppressed_count[key] = self._suppressed_count.get(key, 0) + 1
        return False

    def suppressed_count(self, job_name: str, kind: str) -> int:
        """Return how many alerts have been suppressed for this job+kind since last send."""
        return self._suppressed_count.get((job_name, kind), 0)

    def reset(self, job_name: str, kind: str) -> None:
        """Clear throttle state for a specific job+kind pair."""
        key = (job_name, kind)
        self._last_sent.pop(key, None)
        self._suppressed_count.pop(key, None)

    def reset_all(self) -> None:
        """Clear all throttle state."""
        self._last_sent.clear()
        self._suppressed_count.clear()

    def time_until_next(self, job_name: str, kind: str, now: Optional[datetime] = None) -> Optional[float]:
        """Return seconds until next alert is allowed, or None if not throttled."""
        if now is None:
            now = datetime.utcnow()

        key = (job_name, kind)
        last = self._last_sent.get(key)
        if last is None:
            return None

        elapsed = (now - last).total_seconds()
        remaining = self.cooldown_seconds - elapsed
        return max(0.0, remaining) if remaining > 0 else None
