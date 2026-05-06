"""Entry point for running cronwatcher as a module: python -m cronwatcher"""

import argparse
import sys
import logging
from pathlib import Path

from cronwatcher.config import CronWatcherConfig
from cronwatcher.job_tracker import JobTracker
from cronwatcher.alert_manager import AlertManager
from cronwatcher.log_handler import LogHandler
from cronwatcher.missed_job_checker import MissedJobChecker
from cronwatcher.overdue_checker import OverdueChecker
from cronwatcher.heartbeat import HeartbeatMonitor
from cronwatcher.metrics import MetricsCollector
from cronwatcher.metrics_reporter import MetricsReporter
from cronwatcher.notification_throttle import NotificationThrottle
from cronwatcher.daemon import CronWatcherDaemon

logger = logging.getLogger("cronwatcher")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher",
        description="Monitor cron job execution times and alert on missed or long-running jobs.",
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path("cronwatcher.toml"),
        help="Path to TOML config file (default: cronwatcher.toml)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check cycle and exit (useful for testing)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override log level from config",
    )
    return parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def build_daemon(config: CronWatcherConfig) -> CronWatcherDaemon:
    """Wire up all components from config and return a ready daemon."""
    alert_manager = AlertManager()

    # Set up log handler based on config
    log_cfg = config.log
    log_handler = LogHandler(
        filepath=log_cfg.filepath if log_cfg else None,
        level=log_cfg.level if log_cfg else "INFO",
    )
    alert_manager.register_handler(log_handler)

    # Optional throttle — wrap the alert manager's send if cooldown configured
    throttle = NotificationThrottle(cooldown_seconds=300)

    tracker = JobTracker()
    metrics_collector = MetricsCollector()
    metrics_reporter = MetricsReporter(
        collector=metrics_collector,
        alert_manager=alert_manager,
    )
    alert_manager.register_handler(metrics_reporter._on_alert)

    missed_checker = MissedJobChecker(
        tracker=tracker,
        alert_manager=alert_manager,
        throttle=throttle,
        job_configs=config.jobs,
    )

    overdue_checker = OverdueChecker(
        tracker=tracker,
        alert_manager=alert_manager,
        throttle=throttle,
    )
    for job in config.jobs:
        if job.max_runtime is not None:
            overdue_checker.set_max_runtime(job.name, job.max_runtime)

    heartbeat_monitor = HeartbeatMonitor(
        tracker=tracker,
        alert_manager=alert_manager,
        throttle=throttle,
    )

    return CronWatcherDaemon(
        tracker=tracker,
        missed_checker=missed_checker,
        overdue_checker=overdue_checker,
        heartbeat_monitor=heartbeat_monitor,
        metrics_reporter=metrics_reporter,
        poll_interval=config.poll_interval,
    )


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Config file not found: {args.config}", file=sys.stderr)
        return 1

    try:
        config = CronWatcherConfig.from_toml(args.config)
    except Exception as exc:
        print(f"Failed to load config: {exc}", file=sys.stderr)
        return 1

    log_level = args.log_level or (config.log.level if config.log else "INFO")
    setup_logging(log_level)

    logger.info("Starting cronwatcher with config: %s", args.config)

    try:
        daemon = build_daemon(config)
    except Exception as exc:
        logger.exception("Failed to initialise daemon: %s", exc)
        return 1

    if args.once:
        logger.info("Running single check cycle (--once mode)")
        daemon.run_once()
        return 0

    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Shutting down cronwatcher.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
