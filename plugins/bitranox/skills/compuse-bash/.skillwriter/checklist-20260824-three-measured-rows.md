# skill-writer checklist - compuse-bash (three Quick-reference rows, each corrected by measurement)

Change: three rows. Editing a `.sh` while it executes; `systemd-run --service-type=oneshot` blocking
by default; `ps -o pcpu` being a lifetime average. Each was filed as a claim and each was measured
before shipping, and two of the three shipped DIFFERENT from what was filed.

## PLAN

- [x] Skill type: reference table of shell traps. Test approach: reproduce each claim against the
      real tool on this machine, then a catalogue-wide coverage check, then a text check of the row.
- [x] Scope: three rows, no new section, no frontmatter change. Anchors chosen so the three edits sit
      at disjoint points in the table, and each anchor was re-verified unique against the live file
      immediately before it was applied.

## RED

- [x] Coverage checked with `claim_check.py` over all 100 `skills/*/SKILL.md` and
      `skills/*/references/*.md`, separately per topic, and every verdict was ABSENT with the control
      matching: 1678 control hits for the running-script sweep, 5608 for `systemd-run`, 703 for the
      CPU-sampling sweep. The handful of PRESENT hits on broad terms were read in context and are
      unrelated (a binary-protocol "byte offset" note, an `-ef` test-operator row, an rpyc
      `OneShotServer` row, `is-active` used for process liveness elsewhere).
- [x] Running-script claim reproduced with three arms and a control, on bash 5.3.9. A length-changing
      in-place edit made in an ALREADY-EXECUTED region turned `sleep 4` into `leep 4` and failed on
      `leep: command not found`; `/proc/<pid>/fdinfo` confirmed bash's read offset was a raw byte
      count (40, exactly the shebang plus two lines). Write-new-file-then-rename ran clean, inode
      confirmed changed. A SAME-length in-place edit produced no error at all and silently executed
      the substituted command, which is the quieter and more dangerous mode the entry never mentioned.
- [x] `systemd-run` claim measured on systemd 259: `sleep 3` under the default took 3.031s at exit 0,
      the same call with `--no-block` returned in 0.041s, and `--no-block -- /bin/false` still exited
      0 while the unit went to `failed`. Polling showed a plain oneshot unit reports `activating`
      throughout and then `inactive` or `failed`, never `active`.
- [x] `ps -o pcpu` claim measured in BOTH directions, which is what distinguishes a stale average
      from noise: after a 15s burn followed by idle it read 41.9% while every live method read 0.0%;
      0.4s into a burst after an idle stretch it read 5.3% while the process was at 100%. Field
      numbers checked against `proc(5)` (utime 14, stime 15) and `getconf CLK_TCK` (100).

## GREEN

- [x] Two of the three rows ship DIFFERENT from the claim that was filed, because the measurement
      said so:
  - "a FAST return usually means it already failed" is false. A fast SUCCESS returns just as fast
    (`/bin/true`, 0.039s, exit 0) as a fast failure (`/bin/false`, 0.053s, exit 1). The row states
    what actually discriminates - the exit code, and only in blocking mode - and names `is-active` for
    the `--no-block` case where the launcher's exit code no longer carries the outcome.
  - `top -b -n1` is NOT wrong on this build: it read 0.0% while idle and 100.0% while busy, taking
    ~0.22s per invocation because it double-samples internally. Rather than ship an unverified
    cross-platform claim, the row omits `top` entirely and prescribes only the two methods that were
    confirmed correct here.
- [x] The running-script row states BOTH failure modes, not only the filed one, and gives the safe
      way to change a running script (write new, rename over) with the reason it works: the running
      process holds the old inode open.
- [x] The CPU row points at the shipped tool that already automates the `/proc` delta rather than
      making a hand-rolled recipe the primary answer, and names its owning skill and path.

## REFACTOR

- [x] Anchors verified disjoint before applying: byte offsets compared programmatically for the first
      two, and the third inserted by line index against a uniquely-matching row. All three rows
      survive in the file together, and no pre-existing row was reworded or removed.
- [x] Declined generalising the `top` result to macOS, BSD or BusyBox builds, and declined a caveat
      about `systemd-run --wait`, which failed on this container for a D-Bus reason unrelated to the
      job. Neither is in the shipped text.
- [x] Declined adding explanatory prose about the `ps` accounting model: the file's style is one
      dense row per trap, and the row already carries the mechanism.

## Quality

- [x] ASCII only, verified programmatically over the whole file after applying all three rows.
- [x] Present tense, no session narrative, no machine paths, measured figures stated as evidence.
- [x] Frontmatter untouched; the description already covers interpreting command output, waiting for
      an event and backgrounding.

## Deliverables

- [x] Three Quick-reference rows in `SKILL.md`, applied. No script, so no `tests/` change.
