"""Group jobs into named collections for bulk operations and reporting."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Iterator, Set


@dataclass
class JobGroup:
    name: str
    jobs: Set[str] = field(default_factory=set)

    def add(self, job_name: str) -> None:
        self.jobs.add(job_name)

    def remove(self, job_name: str) -> None:
        self.jobs.discard(job_name)

    def __contains__(self, job_name: str) -> bool:
        return job_name in self.jobs

    def __len__(self) -> int:
        return len(self.jobs)

    def __iter__(self) -> Iterator[str]:
        return iter(self.jobs)


class JobGroupRegistry:
    """Registry that maps group names to sets of job names."""

    def __init__(self) -> None:
        self._groups: Dict[str, JobGroup] = {}
        self._job_index: Dict[str, Set[str]] = defaultdict(set)  # job -> group names

    def create_group(self, group_name: str) -> JobGroup:
        if group_name not in self._groups:
            self._groups[group_name] = JobGroup(name=group_name)
        return self._groups[group_name]

    def add_to_group(self, group_name: str, job_name: str) -> None:
        group = self.create_group(group_name)
        group.add(job_name)
        self._job_index[job_name].add(group_name)

    def remove_from_group(self, group_name: str, job_name: str) -> None:
        if group_name in self._groups:
            self._groups[group_name].remove(job_name)
        self._job_index[job_name].discard(group_name)

    def get_group(self, group_name: str) -> JobGroup | None:
        return self._groups.get(group_name)

    def groups_for_job(self, job_name: str) -> FrozenSet[str]:
        return frozenset(self._job_index.get(job_name, set()))

    def jobs_in_group(self, group_name: str) -> FrozenSet[str]:
        group = self._groups.get(group_name)
        return frozenset(group.jobs) if group else frozenset()

    def jobs_in_any(self, group_names: Iterable[str]) -> FrozenSet[str]:
        result: Set[str] = set()
        for name in group_names:
            result |= self.jobs_in_group(name)
        return frozenset(result)

    def jobs_in_all(self, group_names: Iterable[str]) -> FrozenSet[str]:
        names = list(group_names)
        if not names:
            return frozenset()
        result = self.jobs_in_group(names[0])
        for name in names[1:]:
            result = result & self.jobs_in_group(name)
        return result

    def all_groups(self) -> FrozenSet[str]:
        return frozenset(self._groups.keys())

    def delete_group(self, group_name: str) -> None:
        group = self._groups.pop(group_name, None)
        if group:
            for job in group.jobs:
                self._job_index[job].discard(group_name)
