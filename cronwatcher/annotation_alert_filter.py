"""Alert handler that forwards alerts only for jobs matching an annotation filter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from cronwatcher.alert_manager import Alert
from cronwatcher.job_annotations import AnnotationRegistry


@dataclass
class AnnotationAlertFilter:
    """Wrap a downstream handler and only forward alerts whose job carries
    a specific annotation key (and optionally value)."""

    registry: AnnotationRegistry
    key: str
    value: Optional[Any] = None
    _handlers: List[Callable[[Alert], None]] = field(default_factory=list, init=False, repr=False)

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register a downstream alert handler."""
        self._handlers.append(handler)

    def __call__(self, alert: Alert) -> None:
        job_annotations = self.registry.get_all(alert.job_name)
        if self.key not in job_annotations:
            return
        if self.value is not None and job_annotations[self.key] != self.value:
            return
        for handler in self._handlers:
            handler(alert)

    # Make it usable directly as an AlertManager handler
    def handle(self, alert: Alert) -> None:  # pragma: no cover
        self(alert)
