"""Job priority registry — assign and query priority levels for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional


class Priority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Unknown priority level: {value!r}")


@dataclass
class PriorityRegistry:
    _priorities: Dict[str, Priority] = field(default_factory=dict)

    def set_priority(self, job_name: str, priority: Priority | str) -> None:
        """Assign a priority to a job."""
        if isinstance(priority, str):
            priority = Priority.from_str(priority)
        self._priorities[job_name] = priority

    def get_priority(self, job_name: str) -> Priority:
        """Return the priority for a job, defaulting to NORMAL."""
        return self._priorities.get(job_name, Priority.NORMAL)

    def jobs_at(self, priority: Priority | str) -> List[str]:
        """Return all job names assigned to the given priority level."""
        if isinstance(priority, str):
            priority = Priority.from_str(priority)
        return [name for name, p in self._priorities.items() if p == priority]

    def jobs_above(self, priority: Priority | str) -> List[str]:
        """Return jobs with priority strictly above the given level."""
        if isinstance(priority, str):
            priority = Priority.from_str(priority)
        return [name for name, p in self._priorities.items() if p > priority]

    def all_priorities(self) -> Dict[str, str]:
        """Return a snapshot mapping job names to priority names."""
        return {name: p.name for name, p in self._priorities.items()}

    def reset(self) -> None:
        self._priorities.clear()
