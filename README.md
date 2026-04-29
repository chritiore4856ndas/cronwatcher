# cronwatcher

Lightweight daemon that monitors cron job execution times and alerts on missed or long-running jobs.

## Installation

```bash
pip install cronwatcher
```

## Usage

Add `cronwatcher` to your cron jobs by wrapping your commands:

```bash
# In your crontab
* * * * * cronwatcher --job "backup" --timeout 300 /usr/local/bin/backup.sh
```

Start the monitoring daemon:

```bash
cronwatcher daemon --config /etc/cronwatcher/config.yaml
```

Example `config.yaml`:

```yaml
jobs:
  backup:
    schedule: "* * * * *"
    timeout: 300
    alert_after_missed: 2
  cleanup:
    schedule: "0 3 * * *"
    timeout: 600

alerts:
  email: ops@example.com
  slack_webhook: https://hooks.slack.com/services/...
```

View job status:

```bash
cronwatcher status
```

## Features

- Detects missed cron jobs based on expected schedule
- Alerts when jobs exceed configured timeout thresholds
- Supports email and Slack notifications
- Minimal overhead — runs as a lightweight background daemon

## Requirements

- Python 3.8+
- Linux/macOS

## License

This project is licensed under the [MIT License](LICENSE).