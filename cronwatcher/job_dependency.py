"""Tracks dependencies between cron jobs and alerts when upstream jobs fail."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from cronwatcher.alert_manager import Alert, AlertManager


@dataclass
class DependencyGraph:
    """Directed graph of job dependencies (job -> list of jobs it depends on)."""

    _deps: Dict[str, Set[str]] = field(default_factory=dict)
    _reverse: Dict[str, Set[str]] = field(default_factory=dict)

    def add_dependency(self, job: str, depends_on: str) -> None:
        """Register that *job* requires *depends_on* to have succeeded first."""
        self._deps.setdefault(job, set()).add(depends_on)
        self._reverse.setdefault(depends_on, set()).add(job)

    def dependencies_of(self, job: str) -> Set[str]:
        """Return the set of jobs that *job* directly depends on."""
        return set(self._deps.get(job, set()))

    def dependents_of(self, job: str) -> Set[str]:
        """Return the set of jobs that directly depend on *job*."""
        return set(self._reverse.get(job, set()))

    def all_jobs(self) -> Set[str]:
        return set(self._deps) | set(self._reverse)


@dataclass
class JobDependencyChecker:
    """Checks whether a job's dependencies have completed successfully."""

    graph: DependencyGraph
    alert_manager: AlertManager
    _succeeded: Set[str] = field(default_factory=set)
    _failed: Set[str] = field(default_factory=set)
    _alerted: Set[str] = field(default_factory=set)

    def mark_success(self, job: str) -> None:
        """Record that *job* finished successfully."""
        self._succeeded.add(job)
        self._failed.discard(job)

    def mark_failed(self, job: str) -> None:
        """Record that *job* failed; alert dependents that haven't been warned yet."""
        self._failed.add(job)
        self._succeeded.discard(job)
        for dependent in self.graph.dependents_of(job):
            key = f"{job}->{dependent}"
            if key not in self._alerted:
                self._alerted.add(key)
                alert = Alert(
                    kind="dependency_failed",
                    job=dependent,
                    message=f"Upstream job '{job}' failed; '{dependent}' may not run correctly.",
                )
                self.alert_manager.send(alert)

    def is_ready(self, job: str) -> bool:
        """Return True if all dependencies of *job* have succeeded."""
        return self.graph.dependencies_of(job).issubset(self._succeeded)

    def unmet_dependencies(self, job: str) -> Set[str]:
        """Return the subset of dependencies that have not yet succeeded."""
        return self.graph.dependencies_of(job) - self._succeeded

    def reset(self) -> None:
        """Clear all state (call between scheduling cycles if desired)."""
        self._succeeded.clear()
        self._failed.clear()
        self._alerted.clear()
