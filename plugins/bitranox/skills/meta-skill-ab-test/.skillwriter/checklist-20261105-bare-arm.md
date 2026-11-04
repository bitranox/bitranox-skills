# Review checklist 2026-11-05: the bare-arm sentence in meta-skill-ab-test's SKILL.md

Change: one added sentence under the sandbox paragraph: a `[[variant]]` with
`remove_skill = true` (no `dir`, no `markers`) is a bare arm that runs the plugin without the
skill under test, and a variant's `task_file` gives that arm its own prompt, sealed and recorded
per arm with its sha256 (a bare arm's prompt must not name the missing skill). The description is
untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024);
      the frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`;
      the file is ASCII only.
- [x] "no `dir`, no `markers`": executed. `test_a_bare_variant_refuses_markers_and_a_dir` loads a
      profile whose remove_skill variant names both and gets one ProfileError line for each;
      `test_remove_skill_must_be_a_bool` refuses "yes" and 1; `test_remove_skill_false_still_requires_a_dir`
      keeps the dir rule for every other variant; `test_a_bare_variant_loads_without_dir_and_with_its_own_task_file`
      loads the valid shape.
- [x] "runs the plugin without the skill under test": executed.
      `test_freeze_a_bare_variant_removes_the_skill_and_its_router_entry` freezes Vbare: the skill
      dir is gone, the skill's key in hooks/skill_triggers.json is gone (the other key stays), the
      control's checkout keeps both, and a re-freeze of the reused checkout is accepted.
      `test_install_of_a_bare_arm_asserts_the_skill_is_absent` installs it through the fake
      claude (drift empty, no installed skill dir, no router key), then plants the skill back, an
      empty skill dir, and a router key: each install is refused naming what is present.
      `test_a_bare_arm_gets_its_own_prompt_runs_without_the_skill_and_every_record_names_its_prompt`
      runs a live Vbare and C: the fake claude's transcript lists the installed skills, without
      demo-skill for Vbare and with it for C.
- [x] Mutation-proved: with `shutil.rmtree(skill_dir)` replaced by `pass` (removal skipped) the
      freeze, install and end-to-end tests go RED (3 failed); with the absence check
      (`_absence_drift`) disabled the install test goes RED on the empty-dir case (1 failed);
      the restored file is byte-identical (cmp) and all 5 bare tests pass again.
- [x] "its own prompt": executed. In the same end-to-end test the prompt the fake claude received
      (its `-p` argument, written into the transcript) is task-bare.md's text for Vbare and
      task.md's for C.
- [x] "sealed and recorded per arm with its sha256": executed. The same test reads `seal --json`
      (task_files per arm), the seal journal row, PREREG.md, result.json, each arm journal row,
      `score --json` and the `score` text line (`task=task-bare.md@<sha12>`).
      `test_seal_refuses_a_variant_task_file_that_is_missing_or_empty` (missing, empty, blank),
      `test_run_refuses_an_edited_variant_task_file` (uncommitted and committed edits) and
      `test_run_refuses_a_prompt_whose_sha_differs_from_the_seal_row` show the refusals.

## Probes

- [x] RED/GREEN: one added sentence naming two config keys; probe skipped, reason: the suite
      executes both.
