# Review checklist 2026-11-04: the sandbox sentence in meta-skill-ab-test's SKILL.md

Change: one added sentence under the subcommand table: a live run requires
`[run] sandbox = "bwrap"` in `abtest.toml` (or an explicit `"none"`), and `prune-run` and `score`
show which one each arm ran under. The description is untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024);
      the frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`;
      the file is ASCII only.
- [x] "A live run requires the key": executed. `test_a_run_sealed_without_the_key_dry_runs_but_refuses_a_live_arm`
      runs `abtest.py run` on a sealed profile with no `[run] sandbox`: `--dry-run` exits 0, the
      live run exits 2 with `set sandbox = "bwrap"` on stderr and journals no arm.
      `test_seal_refuses_a_profile_that_names_no_sandbox` shows `seal` refuses it too (exit 2), so
      a new run cannot be frozen without it; `test_a_bad_sandbox_value_is_a_profile_error` refuses
      any value but "bwrap" or "none".
- [x] "or an explicit none": executed. `test_sandbox_none_is_recorded_in_the_journal_the_result_the_score_and_prune_run`
      runs a live arm with `sandbox = "none"`: the arm row carries `sandbox: none`, and so do
      result.json, `score --json`, the `score` text line (`sandbox=none`) and `prune-run --json`.
- [x] "bwrap" really sandboxes: `test_a_bwrap_run_starts_the_session_inside_the_sandbox_argv`
      (fake bwrap recording argv) and `test_a_real_bwrap_sandbox_confines_writes_and_hides_the_real_home`
      (the real bwrap 0.11.1). On the dev box (an LXC container) the kernel refuses a private
      /proc in a new PID namespace, so the real test runs the arm's argv with /proc as an empty
      tmpfs there and says so; a live `bwrap` run on that host is refused by the probe.

## Probes

- [x] RED/GREEN: one added sentence naming a config key; no behaviour-shaping rule: probe
      skipped, reason: the test suite executes the refusal.
