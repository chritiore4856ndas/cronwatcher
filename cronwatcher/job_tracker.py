import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobRecord:
    name: str
    started_at: float
    finished_at: Optional[float] = None
    expected_duration: Optional[float] = None  # seconds
    expected_interval: Optional[float] = None  # seconds between runs
    last_seen_at: Optional[float] = None

    @property
    def is_running(self) -> bool:
        return self.finished_at is None

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is not None:
            return self.finished_at - self.started_at
        return time.time() - self.started_at

    @property
    def is_overdue(self) -> bool:
        if self.expected_duration is None:
            return False
        return self.duration > self.expected_duration

    def finish(self) -> None:
        self.finished_at = time.time()
        self.last_seen_at = self.finished_at


class JobTracker:
    def __init__(self):
        self._jobs: dict[str, JobRecord] = {}

    def start(self, name: str, expected_duration: Optional[float] = None,
              expected_interval: Optional[float] = None) -> JobRecord:
        record = JobRecord(
            name=name,
            started_at=time.time(),
            expected_duration=expected_duration,
            expected_interval=expected_interval,
        )
        self._jobs[name] = record
        return record

    def finish(self, name: str) -> Optional[JobRecord]:
        record = self._jobs.get(name)
        if record and record.is_running:
            record.finish()
        return record

    def get(self, name: str) -> Optional[JobRecord]:
        return self._jobs.get(name)

    def overdue_jobs(self) -> list[JobRecord]:
        return [r for r in self._jobs.values() if r.is_running and r.is_overdue]

    def missed_jobs(self) -> list[JobRecord]:
        now = time.time()
        missed = []
        for record in self._jobs.values():
            if record.expected_interval is None or record.last_seen_at is None:
                continue
            if not record.is_running and (now - record.last_seen_at) > record.expected_interval:
                missed.append(record)
        return missed

    def all_jobs(self) -> list[JobRecord]:
        return list(self._jobs.values())
