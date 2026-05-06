"""DuplicateGuard wraps RunLock and integrates with AlertManager to fire alerts when a job
attempts to start while a previous instance is still running."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.run_lock import RunLock


@dataclass
class DuplicateGuard:
    """Detects duplicate concurrent job starts and emits alerts."""

    alert_manager: AlertManager
    lock: RunLock = field(default_factory=RunLock)

    def start(self, job_name: str, owner_pid: Optional[int] = None) -> bool:
        """Signal that *job_name* is starting.

        Returns True if the start is accepted (no duplicate).
        Returns False and fires an alert if the job is already running.
        """
        if not self.lock.acquire(job_name, owner_pid=owner_pid):
            existing = self.lock.get(job_name)
            held = round(existing.held_for, 1) if existing else "?"
            alert = Alert(
                kind="duplicate",
                job_name=job_name,
                message=(
                    f"Job '{job_name}' started while a previous instance is still running "
                    f"(held for {held}s)"
                ),
            )
            self.alert_manager.send(alert)
            return False
        return True

    def finish(self, job_name: str) -> bool:
        """Signal that *job_name* has finished. Releases the lock."""
        return self.lock.release(job_name)

    def is_running(self, job_name: str) -> bool:
        return self.lock.is_locked(job_name)

    def reset(self) -> None:
        """Clear all locks (e.g. on daemon restart)."""
        self.lock.release_all()
