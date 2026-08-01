---
name: infra-storage-check-zpools
description: Use when monitoring ZFS pool health or running scrubs from a machine, script, or timer - checking capacity, read/write/checksum errors, device faults, or scrub age; sending pool alerts by email; installing a monitoring daemon as a systemd service; or scripting any of that against JSON output. Covers install (uvx/uv/pip and an isolated production install), the layered configuration and its six sections, every subcommand, exit codes, and the library API. Prefer this over hand-rolling `zpool status` parsing, a scrub-plus-sleep shell loop, or a cron job that greps text.
---

# check_zpools

Monitors ZFS pools and alerts on them. Reads `zpool status -j --json-int` (never
scrapes text), checks pools against configured thresholds, emails alerts with
deduplication, runs scrubs, and can run continuously as a systemd daemon.

**Requires OpenZFS 2.3 or newer** - that is the binding constraint, not the operating
system. `zpool status -j --json-int` is what everything here reads, and the `-j` JSON
interface arrived in OpenZFS 2.3; on anything older the command exits non-zero and no
subcommand that touches a pool can work. Verify with `zpool status -j > /dev/null`.

Linux and FreeBSD are the native homes. macOS works through the third-party OpenZFS on
macOS port, and on Windows ZFS is not native at all - the OpenZFS on Windows driver is
still beta, so WSL is the practical route there. Both ports track upstream but lag it,
so check the 2.3 requirement on either rather than assuming it. Python 3.10+.

Two commands are narrower than the rest: `service-install` needs systemd, and
`alias-create` is Linux-only. Everything else runs wherever a readable pool does - so on
FreeBSD, macOS or WSL, drop those two lines from the install sequence below and schedule the
check with whatever that host uses (cron, launchd, a timer of its own).

## Install

Zero-install, always newest - the form used by cron jobs and timers:

```bash
uvx check_zpools@latest check
```

Persistent tool install:

```bash
uv tool install check_zpools      # or: pipx install check_zpools
pip install check_zpools          # inside an existing venv
```

**On a production server, install into an isolated interpreter** so an OS Python
upgrade cannot break it:

```bash
PYTHONINTERPRETER=/opt/python-3.14.0/bin/python
VENV_DIR=/opt/check_zpools/python-3.14.0

sudo "$PYTHONINTERPRETER" -m venv "$VENV_DIR"
sudo "$VENV_DIR/bin/python" -m pip install --upgrade pip uv
sudo "$VENV_DIR/bin/uvx" check_zpools@latest config-deploy --target app
sudo "$VENV_DIR/bin/uvx" check_zpools@latest service-install --uvx-version @latest  # systemd only
sudo "$VENV_DIR/bin/uvx" check_zpools@latest alias-create --all-users                # Linux only
```

`@latest` re-resolves, so a release reaches the host without a redeploy, but uv
caches index metadata briefly - a just-published version can still resolve to the
previous one for a short window (observed on a real host minutes after a release).
Force it with `uvx --refresh` when that matters. Omit `@latest` to pin to whatever
is cached. The **daemon resolves only at startup**, so after a release it keeps
running the old version until `systemctl restart check_zpools`; cron invocations
pick it up on their next run.

## Configure

Write a config file, then check what actually took effect:

```bash
check_zpools config-deploy --target app    # /etc/xdg/check_zpools/config.toml
check_zpools config-deploy --target user   # ~/.config/check_zpools/config.toml
check_zpools config                        # show the merged result
check_zpools config --format json --section zfs
```

Layers merge lowest to highest: **defaults -> app -> host -> user -> .env ->
environment**. Any setting can be overridden by an environment variable named
`CHECK_ZPOOLS___<SECTION>__<KEY>` (note the *triple* underscore after the slug):

```bash
CHECK_ZPOOLS___ZFS__CAPACITY_WARNING_PERCENT=85 check_zpools check
CHECK_ZPOOLS___EMAIL__SMTP_PASSWORD=...  # keep secrets out of the config file
```

Six sections:

| Section          | What it controls                                                                     |
|------------------|--------------------------------------------------------------------------------------|
| `[zfs]`          | Thresholds: capacity warning/critical percent, max scrub age, error counts           |
| `[daemon]`       | Check interval, alert resend interval, pools to monitor, alert-state file            |
| `[scrub]`        | Poll cadence, pool selection, whether and when to mail the summary                   |
| `[alerts]`       | Recipients and subject prefix (used by BOTH the daemon alerts and the scrub summary) |
| `[email]`        | SMTP hosts, sender, credentials, STARTTLS, timeout                                   |
| `[lib_log_rich]` | Structured logging: console, journald, eventlog, Graylog/GELF                        |

A minimal working config:

```toml
[zfs]
capacity_warning_percent = 80
capacity_critical_percent = 90
scrub_max_age_days = 30

[alerts]
alert_recipients = ["admin@example.com"]
subject_prefix = "[ZFS Alert]"

[email]
smtp_hosts = ["smtp.example.com:587"]
from_address = "zfs@example.com"
use_starttls = true
```

**Malformed input degrades rather than crashing.** A value that cannot become
its declared type, or a section written as a scalar, falls back to the default
and is logged. A monitoring daemon must not die on a typo in a file a human
edits. It is logged, so the typo is still findable - check the daemon's output
if a setting seems to be ignored.

## Use

### Monitoring

```bash
check_zpools check                      # one-shot check, human table
check_zpools check --format json        # for scripts and other monitors
```

Exit codes: **0** healthy, **1** warning-level issues, **2** critical. This is
the contract to branch on in a script.

```bash
check_zpools daemon                     # continuous monitoring in the foreground
```

The daemon re-checks on `[daemon] check_interval_seconds`, sends an alert per
new issue, suppresses repeats until `alert_resend_interval_hours` has passed
(unless the severity changed), and emails a recovery notice when an issue
clears. It persists that state across restarts, so a restart does not re-alert
everything.

### Scrubbing

```bash
check_zpools scrub                          # every pool, wait for completion
check_zpools scrub --pool rpool             # one pool (repeatable)
check_zpools scrub --dry-run                # report what would happen, touch nothing
check_zpools scrub --no-wait                # start and return
check_zpools scrub --poll-interval 300      # how often to re-read status while waiting
```

**There is deliberately no timeout.** A scrub on a large pool legitimately runs
for many hours; the command waits for the pool, not for a clock. `--poll-interval`
is only how often the question is asked. Any fixed deadline would eventually
report a healthy-but-slow pool as failed, which is the failure this replaces.

Per pool it will: scrub an idle pool; **adopt** a scrub already running rather
than restart it (restarting fails with "currently scrubbing"); and **skip** a
pool whose scan slot is held by a resilver, reporting why. A refused start is
recorded and the other pools still proceed. Exit **1** if any pool was skipped,
refused, canceled, or its scrub found errors.

A weekly timer entry:

```cron
0 8 * * 0 /usr/local/bin/check_zpools scrub
```

### Service

```bash
check_zpools service-install --uvx-version @latest   # systemd unit, enable + start
check_zpools service-install --no-enable --no-start  # install only
check_zpools service-status                          # human status screen
check_zpools service-status --format json            # poll it from another monitor
check_zpools service-uninstall
```

`service-status --format json` returns the service state, the effective daemon
settings and the currently tracked alerts - the way to watch the watcher.

### Email

```bash
check_zpools send-email --to admin@example.com --subject S --body B \
                        --body-html "<p>B</p>" --attachment /path/file
check_zpools send-notification --to admin@example.com --subject S --message M
```

Use these to prove SMTP works before relying on alerts.

### Convenience

```bash
check_zpools info                        # version and resolved metadata
check_zpools alias-create --all-users    # shell alias (root)
check_zpools alias-delete --all-users
check_zpools --traceback <command>       # full traceback on unexpected errors
```

Run `check_zpools <command> --help` for the exact flags of any subcommand.

## Driving it from a script or another agent

Four subcommands take `--format`: `check`, `scrub`, `service-status` (all
`text|json`) and `config` (`human|json`). The others are actions and report
through their exit code.

On failure, the JSON modes keep stdout **parseable** and emit an error object
naming the exception class, so a caller branches on the class rather than
matching prose. Diagnostics go to stderr; the data stream stays clean.

```console
$ check_zpools check --format json    # on a host without ZFS
{
  "error": {
    "type": "ZFSNotAvailableError",
    "message": "zpool command not found. Please install ZFS utilities."
  }
}
$ echo $?
1
```

That distinction matters: "it ran and the answer is no" (exit 1 with a result
document) is not "it could not run" (exit 1 with an error object).

## Library use

```python
from check_zpools import get_config, print_info
from check_zpools.behaviors import check_pools_once, scrub_pools, deliver_scrub_summary
from check_zpools.config import load_settings
```

`load_settings()` returns the validated `CheckZpoolsConfig`; pass it in, or let
each behaviour load it. `check_pools_once()` returns a `CheckResult` carrying
`PoolStatus` objects and `PoolIssue` findings. `scrub_pools()` returns a
`ScrubCycleResult` whose `has_problems()` decides the exit code.

Types you may have to write yourself:

| Type                 | When you need it                                                        |
|----------------------|-------------------------------------------------------------------------|
| `OutputFormat`       | `TEXT` / `JSON` - the `--format` value for check, scrub, service-status |
| `ConfigOutputFormat` | `HUMAN` / `JSON` - the `config` command's format                        |
| `ScrubRunOptions`    | pool selection, wait, poll cadence, dry-run for a scrub cycle           |
| `EmailMessage`       | recipients, subject, body, body_html, from_address, attachments         |
| `Severity`           | `OK` / `INFO` / `WARNING` / `CRITICAL`                                  |
| `IssueCategory`      | `HEALTH` / `CAPACITY` / `ERRORS` / `SCRUB` / `DEVICE`                   |
| `ScanFunction`       | `SCRUB` / `RESILVER` / ... - which scan a pool is running               |

Exceptions worth catching: `ZFSNotAvailableError` (no zpool on this host),
`ZFSCommandError` (zpool ran and refused - carries `exit_code` and `stderr`),
`ZFSParseError` (its output could not be read).

## Things that surprise people

- **A resilver is not a scrub.** ZFS uses one scan slot for both.
  `PoolStatus.scrub_in_progress` is true only for an actual scrub;
  `resilver_in_progress` covers a pool rebuilding redundancy. Alerts say which.
- **A pool can be ONLINE with a FAULTED device** when redundancy is holding.
  Device-level faults are detected and reported separately; do not read pool
  health alone.
- **Scrub duration is a property of the pool, not the schedule.** Size it that
  way when choosing a cadence; weekly is usual, and a multi-TB pool can take
  most of a day.
- **The daemon caches its version at startup.** After upgrading, restart it.
- **Recipients come from `[alerts]`** for both daemon alerts and scrub
  summaries; `[email]` only says how to connect.
