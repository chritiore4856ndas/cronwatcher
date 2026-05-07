"""Tests for cronwatcher.job_dependency."""
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.job_dependency import DependencyGraph, JobDependencyChecker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def graph() -> DependencyGraph:
    g = DependencyGraph()
    g.add_dependency("report", "extract")
    g.add_dependency("report", "transform")
    g.add_dependency("notify", "report")
    return g


@pytest.fixture()
def alert_manager() -> AlertManager:
    return AlertManager()


@pytest.fixture()
def checker(graph, alert_manager) -> JobDependencyChecker:
    return JobDependencyChecker(graph=graph, alert_manager=alert_manager)


# ---------------------------------------------------------------------------
# DependencyGraph tests
# ---------------------------------------------------------------------------

def test_dependencies_of_returns_correct_set(graph):
    assert graph.dependencies_of("report") == {"extract", "transform"}


def test_dependents_of_returns_correct_set(graph):
    assert graph.dependents_of("extract") == {"report"}


def test_no_dependencies_returns_empty(graph):
    assert graph.dependencies_of("extract") == set()


def test_all_jobs_includes_all_nodes(graph):
    assert {"extract", "transform", "report", "notify"}.issubset(graph.all_jobs())


# ---------------------------------------------------------------------------
# JobDependencyChecker tests
# ---------------------------------------------------------------------------

def test_is_ready_when_all_deps_succeeded(checker):
    checker.mark_success("extract")
    checker.mark_success("transform")
    assert checker.is_ready("report") is True


def test_not_ready_when_some_deps_missing(checker):
    checker.mark_success("extract")
    assert checker.is_ready("report") is False


def test_unmet_dependencies_lists_missing(checker):
    checker.mark_success("extract")
    assert checker.unmet_dependencies("report") == {"transform"}


def test_no_deps_job_is_always_ready(checker):
    assert checker.is_ready("extract") is True


def test_mark_failed_sends_alert_to_dependent(checker, alert_manager):
    received: list[Alert] = []
    alert_manager.register_handler(lambda a: received.append(a))

    checker.mark_failed("extract")

    assert len(received) == 1
    assert received[0].kind == "dependency_failed"
    assert received[0].job == "report"
    assert "extract" in received[0].message


def test_mark_failed_does_not_double_alert(checker, alert_manager):
    received: list[Alert] = []
    alert_manager.register_handler(lambda a: received.append(a))

    checker.mark_failed("extract")
    checker.mark_failed("extract")

    assert len(received) == 1


def test_reset_clears_all_state(checker, alert_manager):
    received: list[Alert] = []
    alert_manager.register_handler(lambda a: received.append(a))

    checker.mark_success("extract")
    checker.mark_failed("transform")
    checker.reset()

    # After reset the same failure should fire the alert again
    checker.mark_failed("transform")
    assert len(received) == 2


def test_mark_success_removes_from_failed(checker):
    checker.mark_failed("extract")
    checker.mark_success("extract")
    checker.mark_success("transform")
    assert checker.is_ready("report") is True
