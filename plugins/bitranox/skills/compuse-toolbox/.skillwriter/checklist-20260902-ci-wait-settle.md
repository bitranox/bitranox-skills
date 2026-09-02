# skill-writer checklist - compuse-toolbox (2026-09-02, ci_wait --settle)

Change: `ci_wait.py` confirms an all-green result before returning it, gated by a new `--settle`
(default 20s, `0` disables). The index row gains the confirmation, the residual window it does not
close, and the `--appear-grace` duration it previously left unquantified.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] The gap is a MEASURED failure of the shipped tool, not a hypothetical. Run against a real
      push, the first poll saw one workflow, it went green, and the tool returned `success` while a
      second workflow for that sha was still being created. `gh run list --json headSha` for the
      same sha then showed two runs, one `in_progress`. A run that has not been CREATED yet is
      indistinguishable from one that does not exist, so `verdict()` computed over a partial set and
      the loop returned on the first all-terminal poll.
- [x] Same shape as the appear-grace one level up: that budget exists because an EMPTY match has
      two causes that look identical. This is the non-empty but INCOMPLETE case, which had no guard.
- [x] RED: four tests written first. `test_a_run_created_after_the_first_green_poll_is_still_waited_for`
      failed against the pre-change source on the intended assertion - the verdict summary read
      `ci=success` with the late workflow absent - and `--settle` did not exist as a keyword.
- [x] Only a SUCCESS is confirmed. A failure returns at once, pinned by a test, because a later run
      cannot rescue a failed one and delaying a red verdict is pure cost.
- [x] Confirming can never turn a green into a timeout: running out of deadline mid-confirmation
      returns the green that was actually seen, which is exactly what the function returned before
      the confirmation existed. Pinned by a test at `deadline_polls=1`.
- [x] The run set is keyed on `(databaseId, workflowName)`, not on a count and not on the id alone:
      a re-run gets a fresh id under the same name, and a row missing the field would collapse every
      run to one key and make a growing set look stable.
- [x] Ran the real tool against a real sha after the change, not only its fixtures: it saw both
      runs, confirmed, and reported `workflow=success ci=success` with both rows in the envelope.
- [x] The confirmation costs one extra poll on every green wait. Five existing call-count assertions
      encoded the old contract and were moved with a comment naming the confirming poll; their state
      assertions are unchanged.
- [x] Three tests driving `main()` now pass `--settle 0`. They are about the unknown-sha warning,
      not about confirming, and without it each sat through a real 20 seconds - the module went from
      0.05s to 60s. The opt-out is the tool's own documented flag rather than a patched clock.
- [x] RETRIEVAL RED, against the pre-change row: an isolated agent asked whether a 40-second green
      verdict naming one of two triggered workflows can be trusted answered `NOT STATED` for the
      protection and `NONE` for the option. Unprompted, it also found the row OVERCLAIMING: "the
      entry's opening promise ... and the observed scenario behavior are in tension; the text does
      not resolve whether that tension means a documented limitation was omitted."
- [x] RETRIEVAL GREEN, against the new row: the same question named `--settle`, quoted the
      mechanism, and correctly bounded the claim to "the run(s) actually observed and settled - not
      ... coverage of the whole commit."
- [x] Both arms asked for a `Skill gaps` section and both answered. Both reported the SAME two gaps:
      the appear-grace was named but never quantified, and the row was silent on a run created AFTER
      a confirmed green. Both are now closed in the row - the duration is stated, and the settle is
      described as BOUNDING that window rather than closing it.
- [x] GREEN diffed against RED in both directions. Nothing RED produced is missing from GREEN: its
      correct refusal to trust the verdict survives, and the tension it flagged is absent from GREEN
      because the text now resolves it, which is the fix rather than a lost result.
- [x] Gap DECLINED, with a reason: knowing how many workflows a sha SHOULD have (parsing
      `.github/workflows` and its trigger filters) is a different tool. It would answer the question
      completely instead of bounding it, and it would have to re-implement GitHub's own event
      matching to do so.
- [x] No session narrative, no operator instructions, no scratch paths, no machine-specific
      addresses in the skill or this artifact.
- [x] Full whole-repo gate green after the final row edit.
