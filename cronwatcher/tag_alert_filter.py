"""Alert filter that suppresses or routes alerts based on job tags."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Set

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_tags import TagRegistry

AlertHandler = Callable[[Alert], None]


@dataclass
class TagAlertFilter:
    """Wraps an :class:`AlertManager` and routes alerts by tag.

    Alerts for jobs whose tags intersect *include_tags* are forwarded;
    alerts for jobs whose tags intersect *exclude_tags* are dropped.
    Exclusion takes precedence over inclusion.

    If both sets are empty every alert is forwarded.
    """

    registry: TagRegistry
    downstream: AlertManager
    include_tags: Set[str] = field(default_factory=set)
    exclude_tags: Set[str] = field(default_factory=set)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def configure(self,
                  include: Optional[Iterable[str]] = None,
                  exclude: Optional[Iterable[str]] = None) -> None:
        """Update the include / exclude tag sets."""
        if include is not None:
            self.include_tags = {t.strip().lower() for t in include if t.strip()}
        if exclude is not None:
            self.exclude_tags = {t.strip().lower() for t in exclude if t.strip()}

    def handle(self, alert: Alert) -> None:
        """Decide whether *alert* should be forwarded to *downstream*."""
        job_tags = self.registry.tags_for_job(alert.job_name)

        # Exclusion wins.
        if self.exclude_tags and job_tags & self.exclude_tags:
            return

        # If an include list is set the job must match at least one tag.
        if self.include_tags and not (job_tags & self.include_tags):
            return

        self.downstream.send(alert)

    def __call__(self, alert: Alert) -> None:  # makes it usable as a handler
        self.handle(alert)
