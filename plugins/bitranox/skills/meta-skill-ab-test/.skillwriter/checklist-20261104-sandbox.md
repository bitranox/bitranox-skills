# Review checklist 2026-11-04: the sandbox sentence in meta-skill-ab-test's SKILL.md

Change: one added sentence under the subcommand table: a live run requires `[run] sandbox` in
`abtest.toml`: `"bwrap"`, `"bwrap-tmpfs-proc"` (the same with an empty `/proc`, for an LXC
container) or an explicit `"none"`; `prune-run` and `score` show which one each arm ran under.
The description is untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024);
      the frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`;
      the file is ASCII only.
- [x] "A live run requires the key": executed. `test_a_run_sealed_without_the_key_dry_runs_but_refuses_a_live_arm`
      runs `abtest.py run` on a sealed profile with no `[run] sandbox`: `--dry-run` exits 0, the
      live run exits 2 with `set sandbox = "bwrap"` on stderr and journals no arm.
      `test_seal_refuses_a_profile_that_names_no_sandbox` shows `seal` refuses it too (exit 2), so
      a new run cannot be frozen without it; `test_a_bad_sandbox_value_is_a_profile_error` refuses
      any value but "bwrap", "bwrap-tmpfs-proc" or "none" (`test_every_sandbox_value_loads` loads all three).
- [x] "or an explicit none": executed. `test_sandbox_none_is_recorded_in_the_journal_the_result_the_score_and_prune_run`
      runs a live arm with `sandbox = "none"`: the arm row carries `sandbox: none`, and so do
      result.json, `score --json`, the `score` text line (`sandbox=none`) and `prune-run --json`.
- [x] Both bwrap values really sandbox: `test_a_bwrap_run_starts_the_session_inside_the_sandbox_argv`
      (fake bwrap recording argv, both values) and `test_a_real_bwrap_sandbox_confines_writes_and_hides_the_real_home`
      (the real bwrap 0.11.1, each value's full production argv). On the dev box (an LXC
      container) the kernel refuses a private /proc in a new PID namespace: the "bwrap" case
      skips with its probe's message, the "bwrap-tmpfs-proc" case runs and passes.
- [x] "for an LXC container": executed. `test_a_bwrap_refused_a_private_proc_names_bwrap_tmpfs_proc_as_the_remedy`
      runs a live `bwrap` arm against a bwrap that refuses only `--proc`: exit 2, and the message
      says `set sandbox = "bwrap-tmpfs-proc"`; on the dev box the real probe says the same.

## Probes

- [x] RED/GREEN: one added sentence naming a config key; no behaviour-shaping rule: probe
      skipped, reason: the test suite executes the refusal.
