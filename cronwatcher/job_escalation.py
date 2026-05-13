"""Escalation policy: re-alert with increasing severity after repeated misses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from cronwatcher.alert_manager import Alert, AlertManager


@dataclass
class EscalationLevel:
    threshold: int          # number of consecutive misses before this level fires
    kind: str               # alert kind override, e.g. "escalated_missed"
    message_suffix: str = ""  # appended to the alert message


@dataclass
class EscalationState:
    job_name: str
    miss_count: int = 0
    last_escalated_at: Optional[datetime] = None
    levels_fired: List[int] = field(default_factory=list)

    def increment(self) -> None:
        self.miss_count += 1

    def reset(self) -> None:
        self.miss_count = 0
        self.last_escalated_at = None
        self.levels_fired.clear()


class EscalationPolicy:
    """Tracks consecutive misses per job and fires escalating alerts."""

    def __init__(
        self,
        alert_manager: AlertManager,
        levels: Optional[List[EscalationLevel]] = None,
    ) -> None:
        self._manager = alert_manager
        self._levels: List[EscalationLevel] = sorted(
            levels or [], key=lambda l: l.threshold
        )
        self._states: Dict[str, EscalationState] = {}

    def add_level(self, level: EscalationLevel) -> None:
        self._levels.append(level)
        self._levels.sort(key=lambda l: l.threshold)

    def record_miss(self, job_name: str, now: Optional[datetime] = None) -> None:
        """Call once per detected miss for *job_name*."""
        now = now or datetime.utcnow()
        state = self._states.setdefault(job_name, EscalationState(job_name))
        state.increment()

        for level in self._levels:
            if (
                state.miss_count >= level.threshold
                and level.threshold not in state.levels_fired
            ):
                msg = f"{job_name} has missed {state.miss_count} consecutive run(s)."
                if level.message_suffix:
                    msg = f"{msg} {level.message_suffix}"
                alert = Alert(kind=level.kind, job_name=job_name, message=msg)
                self._manager.send(alert)
                state.last_escalated_at = now
                state.levels_fired.append(level.threshold)

    def record_success(self, job_name: str) -> None:
        """Reset escalation state when a job completes successfully."""
        if job_name in self._states:
            self._states[job_name].reset()

    def state_for(self, job_name: str) -> Optional[EscalationState]:
        return self._states.get(job_name)

    def all_states(self) -> Dict[str, EscalationState]:
        return dict(self._states)
