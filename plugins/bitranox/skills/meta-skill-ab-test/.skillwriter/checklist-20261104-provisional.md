# Review checklist 2026-11-04: the provisional SKILL.md of meta-skill-ab-test

Change: a new skill file, provisional by its own first sentence: frontmatter (name, a "Use when"
description), the script home and exit codes, one line per subcommand, where the run dir lives
and what `init` names, the cost unit, where an arm's work lives and that judging comes before
`prune-run`, the three do-nots and the paid-arm line. The judge, the report and a worked example
are deferred to the release that ships them (plan Task 16, then M3-M4).

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (under 1024, the commit
      gate's cap); the frontmatter loads with `yaml.safe_load` and holds exactly `name` and
      `description`.
- [x] Every command in the text executed against `scripts/abtest.py` at this commit: `--help` on
      the parser and on each of `init`, `seal`, `run`, `score`, `prune-run` exits 0; `init` lists
      `--repo --base --skills-ref --skill`; `run` lists `--dry-run --only`; every subcommand
      lists `--json` (the parser's own docstring states exit 0 yes / 1 no / 2 could not run).
- [x] `init` writes `abtest.toml`, `task.md`, `PREREG.md` (abtest.py, the init handler) and the
      run dir is `git init`ed there, so `seal` commits into the run dir, not the workpiece.
- [x] `[run]` holds `model` and abprofile.py refuses any model but `opus`; `arm_names()` is
      `["C", *variants]`, so `C` is the control.
- [x] `score` returns `cost_usd`, `per_model` and `main_new_tokens` per arm (abscore.py).
- [x] An arm's branch is `abx/<run_id>/<label>` and `prune-run` deletes every ref under
      `abx/<run_id>/`; the arm's uncommitted work is saved as `arms/<label>/uncommitted.patch`
      (abarm.py `save_uncommitted`), and nothing saves the committed diff, so the text orders
      the judging before the prune.
- [x] `BITRANOX_MEMORY_WRITES=off` is the literal the scripts set (abarm.py, abprofile.py,
      abtest.py); the store guard records and never voids (commit cdd3341c, user decision
      2026-11-04 "Record, don't void").
- [x] redcheck `--corpus-cascade` on the scenario: one hit, the repo CLAUDE.md, sharing only
      ordinary words (skill, repository, cost); no cascade text names the harness. The RED
      answers confirm it: neither tier named a shipped tool.

## Probes (text only, baseline-probe agents, pasted text, quote-back required)

- [x] RED (no skill text, same scenario; haiku and opus): both hand-rolled a harness. Haiku:
      "No shipped skill covers a blind pairwise judge, a per-run cost ledger, or the A/B harness
      itself: those are new work." Opus: "NONE covers the whole procedure ... I would write one
      new driver script", reaching for the RESEARCH probe dir and `ab_interleave_run.py`.
- [x] GREEN (first draft pasted; haiku and opus): both name `scripts/abtest.py` and run
      init, fill, seal, `run --dry-run`, hand the user the paid line, score, judge from the
      diffs, prune-run, then `git status` / `git worktree list` to confirm clean; both quote the
      governing line verbatim and invent no command.
- [x] GREEN gaps closed in the text: where the run dir lives and what `seal` commits into; the
      exact paid line and when to hand it over; the cost unit; judging before `prune-run` and
      where an arm's work lives; what `C` is; the model; what `init`'s options name.
- [x] Final probe on the final text (haiku, five questions): 5 of 5 answered by verbatim quote
      (run dir outside the workpiece and `seal` commits there; the paid line after a clean
      `--dry-run`; USD and new tokens per model; judge before `prune-run`, work on
      `abx/<run>/...` plus `uncommitted.patch`; `C` is the control, `opus` only).

## Gaps declined (deferred to the release that ships the judge and the report)

- The judge procedure, blinding, report format, void rules, the floor's definition, the
  acceptance suite's authoring, runs per arm, store-change adjudication: the first sentence
  says they follow; the subcommand `--help` texts hold the mechanics meanwhile.
- `abtest.toml` field by field: `init` writes a commented skeleton; the guide documents it.
- Choosing the task and the workpiece, and shipping after a verdict: the worked example.
- What a non-clean `--dry-run` means: its own output says what was refused (exit 1 or 2).
