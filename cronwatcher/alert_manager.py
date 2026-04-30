"""Alert manager for cronwatcher — handles missed and long-running job notifications."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    job_name: str
    kind: str  # 'missed' | 'overdue' | 'recovered'
    message: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        ts = self.triggered_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{ts}] {self.kind.upper()} — {self.job_name}: {self.message}"


AlertHandler = Callable[[Alert], None]


class AlertManager:
    """Collects alerts and dispatches them to registered handlers."""

    def __init__(self) -> None:
        self._handlers: List[AlertHandler] = []
        self._history: List[Alert] = []

    def register_handler(self, handler: AlertHandler) -> None:
        """Register a callable that will receive Alert objects."""
        self._handlers.append(handler)

    def send(self, alert: Alert) -> None:
        """Dispatch an alert to all registered handlers and store it."""
        self._history.append(alert)
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception:  # noqa: BLE001
                logger.exception("Alert handler %r raised an error", handler)

    def alert_missed(self, job_name: str, expected_at: datetime) -> Alert:
        msg = f"expected at {expected_at.strftime('%H:%M:%S')} but never started"
        alert = Alert(job_name=job_name, kind="missed", message=msg)
        self.send(alert)
        return alert

    def alert_overdue(self, job_name: str, running_seconds: float, limit_seconds: float) -> Alert:
        msg = f"running for {running_seconds:.1f}s, limit is {limit_seconds:.1f}s"
        alert = Alert(job_name=job_name, kind="overdue", message=msg)
        self.send(alert)
        return alert

    def alert_recovered(self, job_name: str, duration_seconds: float) -> Alert:
        msg = f"finished after {duration_seconds:.1f}s"
        alert = Alert(job_name=job_name, kind="recovered", message=msg)
        self.send(alert)
        return alert

    @property
    def history(self) -> List[Alert]:
        return list(self._history)

    def history_for(self, job_name: str) -> List[Alert]:
        return [a for a in self._history if a.job_name == job_name]

    def clear_history(self) -> None:
        self._history.clear()
