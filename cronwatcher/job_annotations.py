"""Attach arbitrary annotations (key-value metadata) to jobs and query them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional


@dataclass
class AnnotationRegistry:
    """Stores per-job annotations and supports filtering/querying."""

    _data: Dict[str, Dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def annotate(self, job_name: str, key: str, value: Any) -> None:
        """Set or overwrite a single annotation on a job."""
        self._data.setdefault(job_name, {})[key] = value

    def set_annotations(self, job_name: str, annotations: Dict[str, Any]) -> None:
        """Bulk-set annotations, merging with any existing ones."""
        self._data.setdefault(job_name, {}).update(annotations)

    def get(self, job_name: str, key: str, default: Any = None) -> Any:
        """Return the annotation value for *key*, or *default* if absent."""
        return self._data.get(job_name, {}).get(key, default)

    def get_all(self, job_name: str) -> Dict[str, Any]:
        """Return a copy of all annotations for *job_name*."""
        return dict(self._data.get(job_name, {}))

    def remove(self, job_name: str, key: str) -> bool:
        """Remove *key* from a job's annotations.  Returns True if it existed."""
        job_data = self._data.get(job_name)
        if job_data and key in job_data:
            del job_data[key]
            return True
        return False

    def jobs_with_annotation(self, key: str, value: Optional[Any] = None) -> Iterator[str]:
        """Yield job names that have *key* set (optionally matching *value*)."""
        for job, annotations in self._data.items():
            if key in annotations:
                if value is None or annotations[key] == value:
                    yield job

    def clear(self, job_name: str) -> None:
        """Remove all annotations for *job_name*."""
        self._data.pop(job_name, None)
