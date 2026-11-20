# compuse-bash - review 2026-11-20 (waiter for a timer's oneshot run)

Type: reference row in the quick-reference table. Source: a queued contribution after a waiter
gated on `ActiveEnterTimestampMonotonic` polled six hours past a finished run of a timer-driven
`Type=oneshot` unit (`RemainAfterExit=no`) and had to be stopped by hand; the skill was not loaded
when the waiter was written. Scenario for every probe: write a bounded background waiter for the
NEXT run of `nightly-report.service` (timer at :01, oneshot, 5-15 min), armed at 19:58.

- [x] Declined list read first (`skill_decisions.py show compuse-bash`): three entries, none on
      systemd or waiting.
- [x] RED (opus + haiku, the pre-edit waiting rows and the systemd-run row): both wrote sound
      waiters from their own systemd knowledge (haiku: an `InvocationID` baseline plus the state
      leaving `activating`; opus: trigger and inactive-enter counters); neither gated on
      `ActiveEnterTimestampMonotonic` with the task spelled out. Opus flagged a real defect: the
      systemd-run row's "poll `systemctl is-active`" and "poll until the state leaves
      `activating`" are satisfied at once by a unit that ran before, and nothing tells an old run
      from a new one. So the row targets that, not only the incident's property.
- [x] Measured before writing (lxc-pydev, `systemctl --user` transient units):
      `sh -c 'sleep 2; exit 3'` read `activating` with `ActiveEnterTimestampMonotonic`,
      `ExecMainExitTimestampMonotonic` and `InactiveEnterTimestampMonotonic` 0, then `failed`
      with both per-run timestamps set, `ActiveEnterTimestampMonotonic` 0, `ExecMainStatus=3`,
      `Result=exit-code`, `InvocationID` unchanged since the start. The persistent
      pve-bindsnap-autovet.service moved both per-run timestamps across its 20:01 run with
      `ActiveEnterTimestampMonotonic` 0.
- [x] GREEN (opus + haiku, the same excerpt plus the new row): both recorded a per-run property
      at arming and gated on it with `ActiveState` in one `systemctl show` read, read
      `Result`/`ExecMainStatus` only after, and avoided `is-active` and `ActiveEnterTimestamp`,
      quoting the new row for each.
- [x] GREEN gaps closed: the measurement sentence now says it was on a FRESH transient unit (a
      reset at each start was never measured; the rule only needs "differs"); opus held that
      `ExecMainExitTimestampMonotonic` is not set when a start fails before the main process -
      measured with `ExecStartPre=/bin/false` (ended `failed`, `InactiveEnterTimestampMonotonic`
      set, `ExecMainExitTimestampMonotonic=0`), so the row now names
      `InactiveEnterTimestampMonotonic` alone and says why not the exit timestamp.
- [x] Quote-back on the final row (opus + haiku, 5 questions each): see the commit; every
      answer quoted the governing text.
- [x] Declined: timer jitter (`AccuracySec`, `RandomizedDelaySec`) and a manual start between
      arming and the tick (outside the row's subject; the generic ceiling rule covers an
      overrun); the poll interval (the "Waiting for an event" row).

Decisions: d-20261120-dc696a7b
