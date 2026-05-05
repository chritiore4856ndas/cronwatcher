"""Retry policy: decides whether a job should be retried and triggers alerts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from cronwatcher.retry_tracker import RetryTracker
from cronwatcher.alert_manager import AlertManager, Alert


@dataclass
class RetryPolicy:
    tracker: RetryTracker
    alert_manager: AlertManager
    max_retries: int = 3
    notify_on_exhausted: bool = True

    def should_retry(self, job_name: str) -> bool:
        """Return True if the job has not yet exhausted its retry budget."""
        return not self.tracker.is_exhausted(job_name)

    def attempt(self, job_name: str) -> bool:
        """Record a retry attempt. Returns True if more retries are allowed."""
        record = self.tracker.record_attempt(job_name)
        exhausted = record.is_exhausted(self.max_retries)
        if exhausted and self.notify_on_exhausted:
            alert = Alert(
                kind="retries_exhausted",
                job_name=job_name,
                detail=f"Job '{job_name}' failed after {self.max_retries} retries.",
            )
            self.alert_manager.send(alert)
        return not exhausted

    def success(self, job_name: str) -> None:
        """Mark the job as succeeded and clear its retry record."""
        self.tracker.mark_success(job_name)
        self.tracker.reset(job_name)

    def reset(self, job_name: str) -> None:
        self.tracker.reset(job_name)

    def attempts_for(self, job_name: str) -> int:
        record = self.tracker._records.get(job_name)
        return record.attempts if record else 0
