# skill-writer checklist - compuse-toolbox (2026-10-19)

Change: one sentence in the `ci_wait` row of `## Tools` for the new `--queued-grace` option and
its `stuck-queued` verdict; the rest of the table is re-padded by `reformat_tables` because that
row got wider. Skill type: reference (retrieval test).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Inherited context checked with `redcheck --corpus-cascade` from this checkout: clean (WEAK
      evidence), 1587 documents read. Nothing in the cascade names a queued-run verdict.
- [x] RED (haiku, `bitranox:baseline-probe`, the row text without the new sentence, NONE allowed):
      situation "poll 60: release=queued for half an hour, a sibling run of the same workflow on
      the sha already succeeded, this one never got a runner". Answer: NONE; it would "let the tool
      run to its `--timeout` deadline" and listed as a gap that the text "does not say what happens
      to a run that stays queued".
- [x] GREEN (same tier, same situation, the edited row): quoted "A run left `queued` for
      `--queued-grace` seconds (default 900, 0 disables) while nothing else on the sha is still
      going is reported as `stuck-queued`, exit 2, naming the run id and, when a run of the same
      workflow on that sha already succeeded, calling it a likely duplicate trigger; it cancels
      nothing itself." Verbatim in the row.
- [x] GREEN diffed against RED both ways: the wait-out-the-deadline answer is gone; RED's other
      point (check the run with `gh run view`, cancel by hand) survives in GREEN as "cancel that run
      by hand (the tool cancels nothing)". No baseline result lost.
- [x] Skill gaps from GREEN, each decided: what a poll line prints while still inside the grace -
      declined, the row describes verdicts and the per-poll line is unchanged; which runs count as
      "still going" under `--event` - declined, the row's event sentence already defines the
      counted runs and the code applies the check to that same filtered set; the no-runs and
      stuck-queued graces counting from different starts - declined, each states its own start.
- [x] Every behaviour claimed in the sentence checked against `scripts/ci_wait.py` and its tests:
      default 900 and 0 disabling (`_parse_args`, `test_a_grace_of_zero_disables_the_check`), exit 2
      (`_EXIT_CODES`), run id and duplicate wording (`_stuck_queued`), nothing else still going
      (`test_a_queued_run_beside_one_still_running_keeps_the_wait_open`).
- [x] CSO description: unchanged (no new trigger; the tool is reached through the `ci_wait` row).
- [x] Table canonical per `reformat_tables --check`.
- [x] Security scan: prose only; no addresses, hosts or paths added.
