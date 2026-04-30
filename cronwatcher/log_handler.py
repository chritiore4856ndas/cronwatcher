"""Alert handler that writes alerts to a log file or stdout."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwatcher.alert_manager import Alert

logger = logging.getLogger(__name__)


@dataclass
class LogHandler:
    """Writes alerts to a Python logger or a dedicated log file."""

    log_file: Optional[str] = None
    level: int = logging.WARNING
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger("cronwatcher.alerts")
        self._logger.setLevel(self.level)

        if not self._logger.handlers:
            if self.log_file:
                handler: logging.Handler = logging.FileHandler(
                    Path(self.log_file), encoding="utf-8"
                )
            else:
                handler = logging.StreamHandler(sys.stdout)

            formatter = logging.Formatter(
                "%(asctime)s  %(levelname)s  %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    # ------------------------------------------------------------------
    # AlertManager handler protocol
    # ------------------------------------------------------------------

    def __call__(self, alert: Alert) -> None:
        """Receive an alert and write it to the configured log target."""
        severity_map = {
            "missed": logging.ERROR,
            "overdue": logging.WARNING,
            "recovered": logging.INFO,
        }
        log_level = severity_map.get(alert.kind, logging.WARNING)
        self._logger.log(log_level, str(alert))

    def flush(self) -> None:
        """Flush all handlers (useful in tests / shutdown)."""
        for h in self._logger.handlers:
            h.flush()
