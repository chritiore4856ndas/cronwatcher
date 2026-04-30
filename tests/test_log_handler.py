"""Tests for LogHandler."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest

from cronwatcher.alert_manager import Alert, AlertManager
from cronwatcher.log_handler import LogHandler


@pytest.fixture(autouse=True)
def _reset_alert_logger():
    """Remove handlers added during each test so they don't bleed across."""
    yield
    log = logging.getLogger("cronwatcher.alerts")
    for h in list(log.handlers):
        h.close()
        log.removeHandler(h)


def _make_alert(kind: str = "missed", job: str = "backup") -> Alert:
    return Alert(kind=kind, job_name=job, message=f"{kind} alert for {job}")


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_default_handler_uses_stdout(capsys):
    handler = LogHandler(level=logging.DEBUG)
    handler(_make_alert(kind="missed"))
    handler.flush()
    captured = capsys.readouterr()
    assert "missed" in captured.out
    assert "backup" in captured.out


def test_file_handler_writes_to_file():
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp:
        path = tmp.name

    handler = LogHandler(log_file=path, level=logging.DEBUG)
    handler(_make_alert(kind="overdue", job="nightly-sync"))
    handler.flush()

    content = Path(path).read_text()
    assert "overdue" in content
    assert "nightly-sync" in content


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

def test_missed_logs_at_error(caplog):
    handler = LogHandler(level=logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="cronwatcher.alerts"):
        handler(_make_alert(kind="missed"))
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_overdue_logs_at_warning(caplog):
    handler = LogHandler(level=logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="cronwatcher.alerts"):
        handler(_make_alert(kind="overdue"))
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_recovered_logs_at_info(caplog):
    handler = LogHandler(level=logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="cronwatcher.alerts"):
        handler(_make_alert(kind="recovered"))
    assert any(r.levelno == logging.INFO for r in caplog.records)


# ---------------------------------------------------------------------------
# Integration with AlertManager
# ---------------------------------------------------------------------------

def test_alert_manager_integration(capsys):
    manager = AlertManager()
    log_handler = LogHandler(level=logging.DEBUG)
    manager.register_handler(log_handler)

    manager.send("missed", "daily-report", "job did not run")
    log_handler.flush()

    captured = capsys.readouterr()
    assert "daily-report" in captured.out
    assert len(manager.history) == 1
