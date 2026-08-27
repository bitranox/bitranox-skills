# skill-writer checklist - compuse-bash (2026-08-27, /dev/tcp is a bash builtin)

Change: one Quick-reference row. `/dev/tcp/HOST/PORT` is a BASH builtin rather than a real path, so
a port probe running under `sh` reports CLOSED for every port including open ones, with nothing in
the output saying why. Ships with plugin 5.258.0.

Source: a contribution queued by an earlier dream at `rnprivat/machines/proxmox/kpx01`, delivered
now as part of the softdev tree dream's batch.

## PLAN

- [x] Skill type: reference (situation -> rule table). The change adds a situation the table did not
      cover at all, not a refinement of one it did.
- [x] Home chosen by trigger: the symptom is a wrong RESULT from a shell command, which is
      compuse-bash's stated domain. It sits beside the existing grep rows, which fail the same way -
      a confident wrong answer rather than an error.
- [x] Scope: one row, no new section, frontmatter untouched.

## RED

- [x] Coverage checked against the CURRENT shipped content before writing, not from the queue entry:
      `grep -ric "dev/tcp"` over `skills/compuse-bash/` returned 0. Not shipped anywhere in it.
- [x] NO behavioural baseline was dispatched this session. Recorded honestly rather than implied:
      this shipped on the maintainer's explicit instruction to drain the contribution queue, and the
      queue entry itself came from a measured miss (a probe run under dash reported a reachable
      service closed, and the wrong conclusion was acted on).
- [x] The mechanism is a documented property of bash, not a guess: `/dev/tcp` is a bash-only
      redirection target, absent from dash, and Debian/Ubuntu point `/bin/sh` at dash.

## GREEN

- [x] The row states the trigger, the mechanism, WHY nothing warns you (the failure is silent and
      indistinguishable from a real closed port), and two safe forms (`bash -c`, or `nc -z` /
      `socket.create_connection`).
- [x] It also asks for a known-OPEN and a known-CLOSED control port in the SAME run, which is what
      separates "the port is shut" from "this probe cannot open anything at all". That is the part
      that makes the rule self-checking rather than a substitution.
- [x] Placed where retrieval lands: the always-scanned Quick-reference table.
- [x] ASCII only, no em-dashes or typographic tells.
- [x] Table rendered and re-read after the write; `git diff --stat` showed 1 insertion and no
      reflow of neighbouring rows.

## REFACTOR

- [x] No content added beyond the queued item.
- [x] Frontmatter/description unchanged - the existing triggers ("exit codes", "output looks
      ambiguous") already route here.
- [x] Full hook suite green after the change: 2015 passed, 1 skipped.
