# Review checklist 2026-10-31: remote-state waiters and stdout envelopes

Change: two Quick reference rows. (1) A waiter of the form `until ! ssh host cmd | grep -q X`
reads ssh's own failure as "X absent"; read output and exit code separately, 255 or 124 is
unknown, any other code is the remote command's answer (`pgrep`: 0 running, 1 gone). (2) A remote
tool's JSON envelope on stdout is the failure report; ssh's `Warning:` lines on stderr are not.

## Claims and their evidence

- [x] The naive loop declares "gone" on an ssh failure, and the new logic says "unknown": a fake
      ssh returning 255 / 0 with a pid / 1 with nothing, run through both (scratch
      `waitprobe.sh`): naive `down: gone`, new `down: unknown`, `alive`, `gone`.
- [x] `pgrep` exits 0 on a match and 1 on none: measured on this host (`found=0`, `none=1`).

## Probes (text only, haiku, reading the file)

- [x] RED (pre-edit file): Q1 (the waiter) NOT COVERED as a case and no replacement given; Q2 (the
      envelope) reached by inference from the exit-code and stdout/stderr rows.
- [x] GREEN 1: both answered from the new rows, but the probe copied the first draft's snippet
      `[ $rc -eq 0 ] && ! grep -q X`, which never reports `pgrep` as gone (pgrep exits 1 then).
      Rewritten to sort by rc first.
- [x] Final probe on the rewritten row: corrected loop logic (0 running, 1 gone, 255/124 unknown,
      deadline reports unknown), each quoted from the row.

## Gaps declined

- A ready-made waiter script: the row names the logic; a script for one host and one command
  would be a second thing to keep current.
