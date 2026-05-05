"""Tracks retry attempts for failed or missed cron jobs."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class RetryRecord:
    job_name: str
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    succeeded: bool = False
    history: List[datetime] = field(default_factory=list)

    def record_attempt(self) -> None:
        now = datetime.utcnow()
        self.attempts += 1
        self.last_attempt = now
        self.history.append(now)

    def mark_success(self) -> None:
        self.succeeded = True

    def is_exhausted(self, max_retries: int) -> bool:
        return self.attempts >= max_retries


class RetryTracker:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self._records: Dict[str, RetryRecord] = {}

    def get_or_create(self, job_name: str) -> RetryRecord:
        if job_name not in self._records:
            self._records[job_name] = RetryRecord(job_name=job_name)
        return self._records[job_name]

    def record_attempt(self, job_name: str) -> RetryRecord:
        record = self.get_or_create(job_name)
        record.record_attempt()
        return record

    def mark_success(self, job_name: str) -> None:
        record = self.get_or_create(job_name)
        record.mark_success()

    def is_exhausted(self, job_name: str) -> bool:
        record = self._records.get(job_name)
        if record is None:
            return False
        return record.is_exhausted(self.max_retries)

    def reset(self, job_name: str) -> None:
        self._records.pop(job_name, None)

    def all_records(self) -> Dict[str, RetryRecord]:
        return dict(self._records)
