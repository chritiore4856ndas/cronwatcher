"""Detects jobs that are flapping — alternating rapidly between success and failure."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

from cronwatcher.alert_manager import Alert, AlertManager


@dataclass
class FlapState:
    job_name: str
    window: int  # number of recent outcomes to consider
    threshold: int  # min alternations within window to call it flapping
    _history: Deque[bool] = field(default_factory=deque)  # True=success, False=failure
    _alerted: bool = False

    def record(self, success: bool) -> None:
        self._history.append(success)
        if len(self._history) > self.window:
            self._history.popleft()

    def alternation_count(self) -> int:
        """Count how many consecutive pairs differ (True->False or False->True)."""
        hist = list(self._history)
        return sum(1 for a, b in zip(hist, hist[1:]) if a != b)

    def is_flapping(self) -> bool:
        if len(self._history) < 2:
            return False
        return self.alternation_count() >= self.threshold

    def reset_alert(self) -> None:
        self._alerted = False


class FlapDetector:
    """Monitors job outcomes and fires alerts when flapping is detected."""

    def __init__(
        self,
        alert_manager: AlertManager,
        window: int = 6,
        threshold: int = 4,
    ) -> None:
        self._alert_manager = alert_manager
        self._window = window
        self._threshold = threshold
        self._states: Dict[str, FlapState] = {}

    def _get_state(self, job_name: str) -> FlapState:
        if job_name not in self._states:
            self._states[job_name] = FlapState(
                job_name=job_name,
                window=self._window,
                threshold=self._threshold,
            )
        return self._states[job_name]

    def record_success(self, job_name: str) -> None:
        state = self._get_state(job_name)
        state.record(True)
        self._evaluate(state)

    def record_failure(self, job_name: str) -> None:
        state = self._get_state(job_name)
        state.record(False)
        self._evaluate(state)

    def _evaluate(self, state: FlapState) -> None:
        if state.is_flapping() and not state._alerted:
            state._alerted = True
            alert = Alert(
                kind="flapping",
                job_name=state.job_name,
                message=(
                    f"Job '{state.job_name}' is flapping: "
                    f"{state.alternation_count()} alternations in last "
                    f"{len(list(state._history))} outcomes"
                ),
            )
            self._alert_manager.send(alert)
        elif not state.is_flapping():
            state._alerted = False

    def reset(self, job_name: str) -> None:
        self._states.pop(job_name, None)

    def state_for(self, job_name: str) -> Optional[FlapState]:
        return self._states.get(job_name)
