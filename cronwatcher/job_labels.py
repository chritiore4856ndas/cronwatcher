"""Key-value label support for cron jobs, enabling rich filtering and grouping."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Set


@dataclass
class LabelRegistry:
    """Stores and queries key-value labels attached to job names."""

    _labels: Dict[str, Dict[str, str]] = field(default_factory=dict)
    _index: Dict[str, Dict[str, Set[str]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(set)))

    def set_labels(self, job: str, labels: Dict[str, str]) -> None:
        """Attach (or replace) labels for a job."""
        # Remove old index entries for this job
        old = self._labels.get(job, {})
        for k, v in old.items():
            self._index[k][v].discard(job)

        self._labels[job] = dict(labels)
        for k, v in labels.items():
            self._index[k][v].add(job)

    def get_labels(self, job: str) -> Dict[str, str]:
        """Return all labels for a job (empty dict if none)."""
        return dict(self._labels.get(job, {}))

    def jobs_with_label(self, key: str, value: Optional[str] = None) -> Set[str]:
        """Return jobs that have *key*, optionally filtered to a specific *value*."""
        if key not in self._index:
            return set()
        if value is None:
            result: Set[str] = set()
            for jobs in self._index[key].values():
                result |= jobs
            return result
        return set(self._index[key].get(value, set()))

    def jobs_matching_all(self, labels: Dict[str, str]) -> Set[str]:
        """Return jobs that match ALL provided key=value pairs."""
        if not labels:
            return set(self._labels.keys())
        sets = [self.jobs_with_label(k, v) for k, v in labels.items()]
        result = sets[0]
        for s in sets[1:]:
            result = result & s
        return result

    def remove_job(self, job: str) -> None:
        """Remove all labels for a job."""
        self.set_labels(job, {})
        self._labels.pop(job, None)

    def all_jobs(self) -> Set[str]:
        """Return all jobs that have at least one label."""
        return set(self._labels.keys())
