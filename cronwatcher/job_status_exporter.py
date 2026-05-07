"""Exports a snapshot of current job statuses for reporting or API consumption."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.job_tracker import JobTracker
from cronwatcher.job_history import JobHistory
from cronwatcher.schedule_parser import CronSchedule


@dataclass
class JobStatusSnapshot:
    job_name: str
    is_running: bool
    last_start: Optional[float]
    last_finish: Optional[float]
    last_duration: Optional[float]
    last_exit_code: Optional[int]
    run_count: int
    schedule_expr: Optional[str] = None
    is_missed: Optional[bool] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "is_running": self.is_running,
            "last_start": self.last_start,
            "last_finish": self.last_finish,
            "last_duration": self.last_duration,
            "last_exit_code": self.last_exit_code,
            "run_count": self.run_count,
            "schedule_expr": self.schedule_expr,
            "is_missed": self.is_missed,
        }


@dataclass
class JobStatusExporter:
    tracker: JobTracker
    history: JobHistory
    schedules: Dict[str, CronSchedule] = field(default_factory=dict)

    def register_schedule(self, job_name: str, schedule: CronSchedule) -> None:
        self.schedules[job_name] = schedule

    def export_job(self, job_name: str) -> Optional[JobStatusSnapshot]:
        record = self.tracker.get(job_name)
        entries = self.history.entries_for(job_name)
        if record is None and not entries:
            return None

        last_entry = entries[-1] if entries else None
        schedule = self.schedules.get(job_name)

        is_missed: Optional[bool] = None
        if schedule is not None:
            last_run_time = last_entry.start_time if last_entry else None
            is_missed = schedule.is_missed(last_run_time)

        return JobStatusSnapshot(
            job_name=job_name,
            is_running=record.is_running() if record else False,
            last_start=last_entry.start_time if last_entry else None,
            last_finish=last_entry.finish_time if last_entry else None,
            last_duration=last_entry.duration() if last_entry else None,
            last_exit_code=last_entry.exit_code if last_entry else None,
            run_count=len(entries),
            schedule_expr=schedule.expression if schedule else None,
            is_missed=is_missed,
        )

    def export_all(self) -> List[JobStatusSnapshot]:
        known_jobs: set = set(self.tracker.all_job_names())
        known_jobs.update(self.history.all_job_names())
        snapshots = []
        for job_name in sorted(known_jobs):
            snap = self.export_job(job_name)
            if snap is not None:
                snapshots.append(snap)
        return snapshots

    def jobs_currently_running(self) -> List[str]:
        return [s.job_name for s in self.export_all() if s.is_running]

    def jobs_missed(self) -> List[str]:
        return [s.job_name for s in self.export_all() if s.is_missed]
