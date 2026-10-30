# Review checklist 2026-10-30: the stock CLI snapshot refusal

Entry covered: E5, `pct snapshot` on a CT with a bind mount fails `snapshot feature is not
available`, and the skill named only the greyed GUI button, so a CLI user did not match it.

Files: `SKILL.md` (description, When to use bullet, one Troubleshooting row).

## Claims and their evidence

- [x] Message text: pve-guest-common `src/PVE/AbstractConfig.pm` snapshot_prepare:
      `die "snapshot feature is not available\n" if !$class->has_feature('snapshot', ...)`.
      A `die` in a pve CLI command exits 255. "running or stopped" and "creates nothing" are the
      reporter's measurement on pve-container 6.0.18 and 6.1.10; not re-run (no host touched).
- [x] Description length after the edit: 553 characters (under 1024).

## Mechanical checks

- [x] Troubleshooting row fits the existing column widths; reformat_tables.py `Unchanged`.
- [x] Added lines ASCII only, under 100 columns (description excepted: front matter), no
      history-finder hit, no private path.

## Probes (bitranox:baseline-probe, text only)

- [x] RED (opus, pre-edit text): Q3 matched only the general bullet; "The exact CLI message and
      the exit code 255 appear nowhere."
- [x] GREEN (opus): quoted the new row and the new When-to-use bullet.
- [x] GREEN gap "the CLI row omits the daemon-restart cause" -> closed (row now "CLI form of the
      greyed button: not installed, or daemons not restarted").
- [x] Re-probe on the final row (opus): listed both causes with the quote. Gap declined: whether
      another cause (a storage without snapshot support) prints the same message; that is stock
      PVE behaviour for any CT, not this tool's scope.
- [x] Routing: the description now carries the error string; a live routing test is not possible
      where the skill is installed, so routing is recorded as unverified (text check only).
