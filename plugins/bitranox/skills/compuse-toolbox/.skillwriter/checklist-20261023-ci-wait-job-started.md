# skill-writer checklist - compuse-toolbox (2026-10-23)

Change: the `stuck-queued` sentence of the `ci_wait` row in `## Tools` now says the verdict also
needs none of the run's JOBS started, because one job waiting for a runner keeps a run `queued`.
The sentence is rewritten at the same length (310 characters), so the widest cell of the column
keeps its width and no other row re-pads: a one-line diff. Skill type: reference (retrieval test).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Inherited context checked with `redcheck --corpus-cascade` from this checkout: it reported
      STRONG, but every hit shares only generic words (completed, polls, waiter, waiting, stuck)
      with facts about other subjects, the function-word false positive. The behavioural RED below
      did fail, which an answer drawn from inherited context would not have.
- [x] RED (`bitranox:baseline-probe`, the pre-change row pasted, told to load no skill): one run,
      run status `queued` 16 minutes, three of five jobs completed, one in_progress, one waiting
      for a macOS runner. opus: (A) `stuck-queued`, exit 2, quoting the old sentence, and listing
      as a gap "Jobs are never mentioned". haiku: (B) keeps waiting, but only by guessing that "else"
      covers jobs, flagging "whether 'still going' is judged per run or per job" as undecided.
- [x] GREEN (same agent type, the edited sentence pasted, two cases: S1 as above, S2 every job
      still queued), on opus and haiku, 4 cells: both tiers answer S1 (B) keeps waiting and S2 (A)
      `stuck-queued`, exit 2, each quoting "with none of its JOBS yet started (one job awaiting a
      runner keeps a run `queued`)", verbatim in the row.
- [x] GREEN diffed against RED both ways: opus's wrong (A) on S1 is gone; RED's advice to read the
      job list before acting is now what the tool does. No baseline result lost: S2 keeps the
      stuck-queued verdict the duplicate-trigger case needs.
- [x] Skill gaps, each decided:
      - where the grace clock starts (raised by RED and GREEN opus) - closed in `--queued-grace`
        help: "Counted from the first poll that saw the run queued, restarting when it leaves
        queued". Not in the row: the sentence would outgrow the column and re-pad the table.
      - what counts as a started job - declined, both GREEN tiers read in_progress and completed as
        started from the parenthetical, matching `_JOB_STARTED`.
      - scope of "no other run going" - declined, the probe excerpt elided the row's own "Runs are
        asked for by sha"; the full row scopes it.
      - no positive keep-waiting sentence, state values, exit-code meaning - declined, the usage
        column states exit 0/1/2 and the row opens with what the tool waits for.
- [x] Every behaviour claimed checked against `scripts/ci_wait.py` and its tests: none of its jobs
      started (`_stuck_queued`, `test_a_queued_run_with_a_started_job_is_waited_out_to_its_verdict`),
      unreadable jobs keep waiting (`test_an_unreadable_job_list_never_proves_a_run_stuck`), the
      duplicate-trigger verdict kept (`test_a_queued_run_whose_jobs_are_all_queued_is_still_stuck`),
      `gh_run_started` on the real run 39932914131 answered True.
- [x] CSO description: unchanged (no new trigger).
- [x] Table canonical per `reformat_tables --check`.
- [x] Security scan: prose only; no addresses, hosts or paths added.
