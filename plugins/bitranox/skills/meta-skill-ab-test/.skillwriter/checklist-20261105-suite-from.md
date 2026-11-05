# Review checklist 2026-11-05: the suite_from sentence in meta-skill-ab-test's SKILL.md

Change: one added sentence after the bare-arm sentence: an acceptance suite kept outside the
workpiece is named by `[floor] suite_from = "<absolute path>"`; `seal` copies it from there, and
`suite` stays the path the sealed copy takes in each arm's worktree. The description is untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024);
      the frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`;
      the file is ASCII only.
- [x] "named by suite_from = <absolute path>": executed.
      `test_suite_from_loads_as_an_absolute_path_and_defaults_to_none` loads it (and None when
      unset); `test_suite_from_must_be_an_absolute_path` refuses a relative path, a non-string, an
      empty value and a placeholder; `test_suite_from_without_a_suite_is_refused` refuses it
      without `floor.suite`.
- [x] "seal copies it from there": executed.
      `test_seal_copies_the_suite_from_suite_from_and_every_floor_runs_it` seals a run whose
      workpiece has no suite: the sealed copy equals the outside file byte for byte, the stamp
      and the seal row record `suite_from` and its sha256, and the workpiece's git status is
      unchanged. `test_seal_refuses_a_suite_from_that_does_not_exist` refuses a missing file
      (exit 2, no seal row, no sealed/). `test_without_suite_from_seal_still_reads_the_workpiece_and_records_none`
      keeps the old source when unset.
- [x] "suite stays the path the sealed copy takes in each arm's worktree": executed. The same
      first test runs a live arm through the fake claude; its floor's suite step runs the sealed
      copy at `acceptance/check.sh` and passes (rc 0).
      `test_run_refuses_a_suite_from_copy_whose_hash_differs_from_the_seal` shows the outside file
      moving on changes nothing, and a committed edit of the sealed copy is refused.
- [x] Mutation-proved: with the `suite_from` branch of `_seal_suite` disabled, the three
      suite_from seal and run tests go RED (3 failed); restored, all 4 pass.

## Probes

- [x] RED/GREEN: one added sentence naming one config key; probe skipped, reason: the suite
      executes it.
