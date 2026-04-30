"""Parse cron schedule expressions and determine if a job is overdue."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from croniter import croniter


@dataclass
class CronSchedule:
    """Represents a parsed cron schedule for a named job."""

    job_name: str
    expression: str
    grace_period_seconds: int = 60

    def __post_init__(self):
        if not croniter.is_valid(self.expression):
            raise ValueError(
                f"Invalid cron expression for job '{self.job_name}': {self.expression!r}"
            )

    def last_expected_run(self, now: Optional[datetime] = None) -> datetime:
        """Return the most recent scheduled time before `now`."""
        now = now or datetime.utcnow()
        it = croniter(self.expression, now)
        return it.get_prev(datetime)

    def next_expected_run(self, now: Optional[datetime] = None) -> datetime:
        """Return the next scheduled time after `now`."""
        now = now or datetime.utcnow()
        it = croniter(self.expression, now)
        return it.get_next(datetime)

    def is_missed(self, last_run: Optional[datetime], now: Optional[datetime] = None) -> bool:
        """Return True if the job missed its last scheduled window.

        A job is considered missed when the last expected run time has passed
        (plus the grace period) and `last_run` is either None or predates that
        scheduled time.
        """
        now = now or datetime.utcnow()
        expected = self.last_expected_run(now)
        deadline = expected.timestamp() + self.grace_period_seconds
        if now.timestamp() < deadline:
            return False
        if last_run is None:
            return True
        return last_run.timestamp() < expected.timestamp()


class ScheduleRegistry:
    """Holds all registered cron schedules."""

    def __init__(self):
        self._schedules: dict[str, CronSchedule] = {}

    def register(self, schedule: CronSchedule) -> None:
        self._schedules[schedule.job_name] = schedule

    def get(self, job_name: str) -> Optional[CronSchedule]:
        return self._schedules.get(job_name)

    def all(self) -> list[CronSchedule]:
        return list(self._schedules.values())

    def __len__(self) -> int:
        return len(self._schedules)
