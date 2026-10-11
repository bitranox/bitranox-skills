# skill-writer checklist - compuse-bash (2026-10-11, ugrep complexity-limit row)

Change: one new Quick-reference row (reference skill) on the interactive `grep` function failing
with `ugrep: error ... exceeds complexity limits` for bounded repeats like `.{0,160}`.

- [x] Reproduced against the live tool. `type grep` reports a shell function wrapping ugrep.
      `grep -oE '.{0,160}needle.{0,160}' a.jsonl` exits 2 with
      `ugrep: error: error at position 84 ... [\x80-\xbf]*){0,160} ... exceeds complexity limits`.
      The same pattern with `{0,20}` exits 0. `bash -c "grep -oE ..."` and
      `LC_ALL=C /usr/bin/grep -oE ...` both exit 0 with identical 1635-byte output.
- [x] No existing text covered it: the only grep-function row is the `-q`/`-v` exit-status row,
      which is a different defect; searched the whole plugin for ugrep and complexity text.
- [x] RED (haiku and sonnet, given the error text, no skill): both inferred ugrep from the message
      and proposed `/usr/bin/grep`; both reported as gaps that they could not confirm the cause,
      did not know the shell function is the mechanism, and did not know `bash -c grep` also works.
      The error message is the only recognisable signal, so the row quotes it.
- [x] GREEN (haiku and sonnet, row pasted, different bounds `{0,300}`): both quoted the
      recognition sentence and the workaround verbatim, proposed `type grep` as the confirming step
      and a small-bound control, and gave `LC_ALL=C /usr/bin/grep` with redirect and exit status.
- [x] Skill gaps reported by GREEN, each closed or declined:
  - meaning of `LC_ALL=C` windows: closed (row now says `.` matches one byte).
  - exact threshold between `{0,20}` and `{0,160}`: declined; it depends on the ugrep build and
    only the observed pass/fail points are stated.
  - redirect-and-exit-status capture form: declined; the row says to redirect and read the
    status, the full idiom is in the existing rows of this skill.
  - `/usr/bin/grep` being GNU: declined; the existing `-q -v` row already relies on it.
- [x] Diff GREEN against RED both ways: nothing the RED runs produced was lost.
- [x] Description unchanged; table re-checked canonical with the repo table formatter.
- [x] ASCII only; no addresses, hostnames or machine paths other than `/usr/bin/grep`.
