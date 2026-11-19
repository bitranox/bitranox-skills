# skill-writer checklist - compuse-toolbox (2026-11-19, mutation_arm restores when killed)

- [x] Receipt fresh; Step 0b `show --kind rejected,removed --full` run: no rejected or removed
      entry touches mutation_arm's restore or signal handling; the live rule
      `mutation-arm-one-node-id-per-test` keeps both its anchors.
- [x] Premises checked against the code: `scripts/mutation_arm.py` turns SIGTERM, SIGHUP, SIGINT
      and SIGBREAK into `ArmInterrupted` (`_STOP_SIGNALS`), restores in the arm's `finally`, and
      `_interrupted` prints `stopped by <SIG>; every mutated source was restored` (or RESTORE
      FAILED) and returns 128 + signum; `run_battery` has no handler for it, so no later arm, no
      final baseline and no report; arm logs are written per finished arm (`_write_log`).
      `scripts/_arm_journal.py`: journal under `MUTATION_ARM_STATE_DIR` else the per-user state
      dir, written before the first source write; `recover` restores an unchanged mutant, keeps
      an edited file as a conflict; `Recovery.blocking` names the original's copy and the
      journal dir to delete, and refuses a file a live run holds; an unwritable root raises,
      which `main` reports as `refused before mutating`, exit 2.
- [x] Tests for those claims pass: `tests/test_mutation_arm.py` and `tests/test_arm_journal.py`
      `-k "sig or live or unwritable or edited"`, 10 passed (exit 128 + signal, restored source,
      RESTORED after SIGKILL, edited file refused with exit 2, live run refused, unwritable root).
- [x] RED (opus and haiku, pre-edit row): both quoted "killing it by hand skips the restore and
      leaves a mutated file on disk" for a harness SIGTERM, answered NONE for the exit code and
      for what the next start does after a SIGKILL, and told the reader to restore by hand.
- [x] GREEN (opus and haiku, new row): both quoted "A kill from outside restores too" for
      SIGTERM (exit 143) and the journal sentence for SIGKILL and the edited-file refusal.
- [x] Gaps closed from GREEN: a battery stops at the signalled arm with no final baseline and no
      report (no envelope under `--json`), so finished arms' output survives only in their
      `--log-dir` logs; the refusal names that killed run's journal directory, deleted after
      comparing and restoring; the exit list gains `128 + N`.
- [x] Final re-probe on the final row (opus and haiku, battery and edited-file questions) answered
      each with a quote and reported no new undecided gap.
- [x] Gaps declined: the per-user state dir's exact path (the refusal line prints the directory,
      `_arm_journal.py` `Recovery.blocking`; the `_arm_journal.py` module docstring names the
      default); whether to keep a deliberate hand edit or the original (the reader's judgment);
      telling a live-run refusal from a killed-run one (the two lines differ,
      `_arm_journal.py` `Recovery.blocking`: "is being mutated by another mutation_arm run").
- [x] No other stale kill/restore sentence: grep over SKILL.md and references/ for "hand-kill",
      "kill", "mutated file" leaves only the edited row.
- [x] Table re-padded by the formatter only (`--check` reports it unchanged); description
      unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261119-29328a03
