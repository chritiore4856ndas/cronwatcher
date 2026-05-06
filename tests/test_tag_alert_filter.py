"""Tests for cronwatcher.tag_alert_filter."""
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_tags import TagRegistry
from cronwatcher.tag_alert_filter import TagAlertFilter


@pytest.fixture()
def registry() -> TagRegistry:
    reg = TagRegistry()
    reg.register("backup", ["critical", "nightly"])
    reg.register("report", ["nightly", "email"])
    reg.register("cleanup", ["maintenance"])
    return reg


@pytest.fixture()
def downstream() -> AlertManager:
    return AlertManager()


@pytest.fixture()
def tag_filter(registry: TagRegistry, downstream: AlertManager) -> TagAlertFilter:
    return TagAlertFilter(registry=registry, downstream=downstream)


def _alert(job: str, kind: str = "missed") -> Alert:
    return Alert(job_name=job, kind=kind, message=f"{kind} alert for {job}")


# ------------------------------------------------------------------ #
# no filters — everything passes through
# ------------------------------------------------------------------ #

def test_no_filter_forwards_all(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter.handle(_alert("backup"))
    handler.assert_called_once()


# ------------------------------------------------------------------ #
# include filter
# ------------------------------------------------------------------ #

def test_include_tag_allows_matching_job(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter.configure(include=["critical"])
    tag_filter.handle(_alert("backup"))
    handler.assert_called_once()


def test_include_tag_blocks_non_matching_job(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter.configure(include=["critical"])
    tag_filter.handle(_alert("cleanup"))
    handler.assert_not_called()


# ------------------------------------------------------------------ #
# exclude filter
# ------------------------------------------------------------------ #

def test_exclude_tag_blocks_matching_job(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter.configure(exclude=["maintenance"])
    tag_filter.handle(_alert("cleanup"))
    handler.assert_not_called()


def test_exclude_does_not_block_unrelated_job(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter.configure(exclude=["maintenance"])
    tag_filter.handle(_alert("backup"))
    handler.assert_called_once()


# ------------------------------------------------------------------ #
# exclusion takes precedence over inclusion
# ------------------------------------------------------------------ #

def test_exclude_overrides_include(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter.configure(include=["nightly"], exclude=["critical"])
    # backup has both 'nightly' (included) and 'critical' (excluded) — should be blocked
    tag_filter.handle(_alert("backup"))
    handler.assert_not_called()


def test_callable_interface(tag_filter: TagAlertFilter, downstream: AlertManager) -> None:
    handler = MagicMock()
    downstream.register_handler(handler)
    tag_filter(_alert("report"))  # __call__ delegates to handle
    handler.assert_called_once()
