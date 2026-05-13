"""Tag-based filtering and grouping for cron jobs."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set


@dataclass
class TagRegistry:
    """Maintains a mapping between tags and job names."""

    _tag_to_jobs: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _job_to_tags: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    def register(self, job_name: str, tags: Iterable[str]) -> None:
        """Associate *tags* with *job_name*."""
        for tag in tags:
            tag = tag.strip().lower()
            if not tag:
                continue
            self._tag_to_jobs[tag].add(job_name)
            self._job_to_tags[job_name].add(tag)

    def jobs_for_tag(self, tag: str) -> Set[str]:
        """Return all job names that carry *tag*."""
        return set(self._tag_to_jobs.get(tag.strip().lower(), set()))

    def jobs_for_tags(self, tags: Iterable[str], match_all: bool = False) -> Set[str]:
        """Return jobs matching any (or all) of the supplied *tags*.

        Parameters
        ----------
        tags:
            Iterable of tag strings to query.
        match_all:
            When *True* only jobs that carry **every** supplied tag are
            returned; otherwise the union is returned.
        """
        tag_list = [t.strip().lower() for t in tags if t.strip()]
        if not tag_list:
            return set()
        sets = [self.jobs_for_tag(t) for t in tag_list]
        if match_all:
            result = sets[0]
            for s in sets[1:]:
                result = result & s
            return result
        result: Set[str] = set()
        for s in sets:
            result |= s
        return result

    def tags_for_job(self, job_name: str) -> Set[str]:
        """Return all tags registered for *job_name*."""
        return set(self._job_to_tags.get(job_name, set()))

    def all_tags(self) -> List[str]:
        """Return sorted list of every known tag."""
        return sorted(self._tag_to_jobs.keys())

    def all_jobs(self) -> List[str]:
        """Return sorted list of every registered job name."""
        return sorted(self._job_to_tags.keys())

    def remove_job(self, job_name: str) -> None:
        """Remove *job_name* and all its tag associations."""
        for tag in list(self._job_to_tags.pop(job_name, set())):
            self._tag_to_jobs[tag].discard(job_name)
            if not self._tag_to_jobs[tag]:
                del self._tag_to_jobs[tag]

    def rename_tag(self, old_tag: str, new_tag: str) -> None:
        """Rename *old_tag* to *new_tag* across all job associations.

        If *old_tag* does not exist this is a no-op.  If *new_tag* already
        exists the job sets are merged.
        """
        old_tag = old_tag.strip().lower()
        new_tag = new_tag.strip().lower()
        if not old_tag or not new_tag or old_tag not in self._tag_to_jobs:
            return
        for job_name in self._tag_to_jobs.pop(old_tag):
            self._tag_to_jobs[new_tag].add(job_name)
            self._job_to_tags[job_name].discard(old_tag)
            self._job_to_tags[job_name].add(new_tag)

    def to_dict(self) -> Dict[str, List[str]]:
        """Serialise as ``{job_name: [tag, ...]}`` mapping."""
        return {job: sorted(tags) for job, tags in self._job_to_tags.items()}
