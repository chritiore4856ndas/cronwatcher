"""Audit log for cron job lifecycle events.

Records every significant state change (start, finish, alert, skip, etc.)
so operators can reconstruct what happened to any job over time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AuditEvent:
    """A single audit log entry for a job."""

    job_name: str
    event_type: str          # e.g. "start", "finish", "alert", "skip", "pause"
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    # ---- serialisation ------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_name": self.job_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def __str__(self) -> str:
        detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
        base = f"[{self.timestamp.isoformat()}] {self.event_type.upper()} {self.job_name!r}"
        return f"{base} — {detail_str}" if detail_str else base


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class JobAuditLog:
    """In-memory audit log that records events for every tracked job.

    Events are stored in insertion order.  The log is intentionally
    unbounded by default; callers that care about memory should call
    ``trim`` periodically or set *max_events_per_job*.
    """

    def __init__(self, max_events_per_job: Optional[int] = None) -> None:
        self._log: Dict[str, List[AuditEvent]] = {}
        self._max = max_events_per_job

    # ---- write --------------------------------------------------------

    def record(
        self,
        job_name: str,
        event_type: str,
        timestamp: Optional[datetime] = None,
        **details: Any,
    ) -> AuditEvent:
        """Append a new event for *job_name* and return it."""
        ts = timestamp or datetime.utcnow()
        event = AuditEvent(
            job_name=job_name,
            event_type=event_type,
            timestamp=ts,
            details=dict(details),
        )
        bucket = self._log.setdefault(job_name, [])
        bucket.append(event)
        if self._max is not None and len(bucket) > self._max:
            # drop oldest entries to stay within the cap
            del bucket[: len(bucket) - self._max]
        return event

    # ---- read ---------------------------------------------------------

    def events_for(self, job_name: str) -> List[AuditEvent]:
        """Return all recorded events for *job_name* (oldest first)."""
        return list(self._log.get(job_name, []))

    def events_by_type(
        self, job_name: str, event_type: str
    ) -> List[AuditEvent]:
        """Filter events for *job_name* by *event_type*."""
        return [
            e for e in self.events_for(job_name) if e.event_type == event_type
        ]

    def all_events(self) -> List[AuditEvent]:
        """Return every recorded event across all jobs, sorted by timestamp."""
        events: List[AuditEvent] = []
        for bucket in self._log.values():
            events.extend(bucket)
        events.sort(key=lambda e: e.timestamp)
        return events

    def known_jobs(self) -> List[str]:
        """Return job names that have at least one audit event."""
        return list(self._log.keys())

    # ---- maintenance --------------------------------------------------

    def trim(self, job_name: str, keep: int) -> int:
        """Keep only the *keep* most-recent events for *job_name*.

        Returns the number of events that were dropped.
        """
        bucket = self._log.get(job_name)
        if not bucket or len(bucket) <= keep:
            return 0
        drop = len(bucket) - keep
        del bucket[:drop]
        return drop

    def clear(self, job_name: Optional[str] = None) -> None:
        """Clear events for *job_name*, or all events if *job_name* is None."""
        if job_name is None:
            self._log.clear()
        else:
            self._log.pop(job_name, None)
