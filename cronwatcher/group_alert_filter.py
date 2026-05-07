"""Alert handler that forwards alerts only for jobs belonging to specific groups."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Set

from cronwatcher.alert_manager import Alert
from cronwatcher.job_grouping import JobGroupRegistry

AlertHandler = Callable[[Alert], None]


@dataclass
class GroupAlertFilter:
    """Filters alerts to only those whose job belongs to at least one configured group."""

    registry: JobGroupRegistry
    _allowed_groups: Set[str] = field(default_factory=set, init=False)
    _handlers: List[AlertHandler] = field(default_factory=list, init=False)

    def configure(self, group_names: Iterable[str]) -> None:
        """Set the groups whose jobs should pass through."""
        self._allowed_groups = set(group_names)

    def add_handler(self, handler: AlertHandler) -> None:
        self._handlers.append(handler)

    def __call__(self, alert: Alert) -> None:
        if not self._allowed_groups:
            # No filter configured — forward everything
            for h in self._handlers:
                h(alert)
            return

        job_groups = self.registry.groups_for_job(alert.job_name)
        if job_groups & self._allowed_groups:
            for h in self._handlers:
                h(alert)
