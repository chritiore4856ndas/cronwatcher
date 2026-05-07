"""Export job annotations to plain dicts (e.g. for JSON/metrics endpoints)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from cronwatcher.job_annotations import AnnotationRegistry


@dataclass
class AnnotationExporter:
    """Converts registry contents into serialisable structures."""

    registry: AnnotationRegistry

    def export_job(self, job_name: str) -> Dict[str, Any]:
        """Return all annotations for a single job."""
        return {"job": job_name, "annotations": self.registry.get_all(job_name)}

    def export_all(self, job_names: List[str]) -> List[Dict[str, Any]]:
        """Return annotation snapshots for every job in *job_names*."""
        return [self.export_job(name) for name in job_names]

    def jobs_with_key(self, key: str, value: Any = None) -> List[str]:
        """Convenience wrapper around the registry query."""
        return list(self.registry.jobs_with_annotation(key, value))
