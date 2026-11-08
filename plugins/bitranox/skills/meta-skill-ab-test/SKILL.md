---
name: meta-skill-ab-test
description: Use when comparing a shipped bitranox skill against one or more modified variants on one real task in the real project repository - judging exact cost and token usage per run and which code came out better, pairwise from the diffs - or when tempted to judge a skill change from transcripts alone, to hand-roll an A/B harness, or to re-run an arm that already cost money. Keywords - A/B test, variant, control arm, abtest, pre-registration, PREREG, seal, void arm, floor, workpiece.
---

# A/B testing a skill against its variants (meta-skill-ab-test)

Provisional text: the harness ships and runs; the full guide (judge, report, worked example)
follows in a later release. Every command below is `python3 <this skill's dir>/scripts/abtest.py
<subcommand> <run_dir> [--json]`; `--help` on each subcommand lists its options. Exit 0 yes, 1 no,
2 could not run. Each arm runs the shipped `claude -p` in a nested git worktree of the real
repository with its own config dir and a frozen plugin checkout; the memory store is not written
(`BITRANOX_MEMORY_WRITES=off`) and any change to it is recorded for adjudication, never a void.

| Subcommand  | One line                                                                                          |
|-------------|---------------------------------------------------------------------------------------------------|
| `init`      | writes `abtest.toml` (the profile), `task.md` and `PREREG.md` skeletons into a new run dir        |
| `seal`      | validates them, records the acceptance suite's hash and commits them; the inputs are frozen       |
| `run`       | the serial interleaved arms (`--dry-run` first, `--only C` for one arm); resumes from its journal |
| `score`     | per-arm cost from the stream, floor result, void rules and store-change flags                     |
| `prune-run` | deletes the run's branches, worktrees and hook dirs in the workpiece; leaves nothing of the run   |

A live run requires `[run] sandbox` in `abtest.toml`: `"bwrap"`, `"bwrap-host-proc"` (the same
with the host's `/proc` read-only, for an LXC container; other processes' command lines stay
readable there) or an explicit `"none"`; `prune-run` and `score` show which one each arm ran under.
A `[[variant]]` with `remove_skill = true` (no `dir`, no `markers`) is a bare arm that runs the
plugin without the skill under test, and a variant's `task_file` gives that arm its own prompt,
sealed and recorded per arm with its sha256 (a bare arm's prompt must not name the missing skill).
An acceptance suite kept outside the workpiece is named by `[floor] suite_from = "<absolute path>"`:
`seal` copies it from there, and `suite` stays the path the sealed copy takes in each arm's worktree.

The run dir is a new directory OUTSIDE the workpiece, its own git repo (`seal` commits there,
never into the workpiece); `init --repo <workpiece> --base <commit> --skills-ref <plugin commit>
--skill <name>` names the repository, the commit every arm starts from, the frozen plugin
checkout and the skill under test, and the profile's `[run]` holds the model (`opus` only) and
the arms, `C` being the shipped control. `score` reports USD and new tokens per model from each
arm's stream. An arm's work is its commits on the workpiece branch `abx/<run>/...` plus
`arms/<label>/uncommitted.patch`: judge the diffs pairwise BEFORE `prune-run`, which deletes those
branches and keeps the run dir; first it writes every branch of the run (set-aside attempts and killed
arms included, which an arm's own `bundle.git` does not hold) into `<run dir>/branches.bundle`, and
deletes nothing if that fails. It also removes, by exact path, a worktree an arm registered itself
under `arms/` (a parallel node's), with its branch. Never delete a run dir by hand: it can hold the
pinned plugin checkout (`--skills-repo` worktree), still registered in the skills repository, that
later runs start from. Remove the arm data inside it and leave that checkout.

Each `score` line also reads three fields from the arm dir; they inform, they never void. Each
field shows `-` when its own source is absent: `subagents=` when the arm has no `transcripts/`
dir, `ideas=` when it has neither `stream.jsonl` nor a subagent transcript, `suite=` when the
floor ran no suite step. `subagents=N(max M at once)` counts the arm's subagent transcripts
(`agent-*.jsonl` under `transcripts/`) and the most whose first-to-last timestamp spans overlap
at one instant (a background Agent call returns at once, so the stream alone cannot show
parallelism; `max 1` means no two spans overlapped). `ideas=1x2,3x1` reads idea 1 with 2
distinct marker lines, idea 3 with 1, and prints the first line of each idea below the arm.
Markers are read from the writing tool calls (Write, Edit, MultiEdit, NotebookEdit, a Bash
redirect or `tee`, into any file) in `stream.jsonl` and in the subagent transcripts, a call
found in both counted once, because `.bitranox/` is untracked and in no branch; a marker only
quoted in a prompt, a brief or a read-back does not count, a write by any other route
(`sed -i`, a script) is not seen, and `none` means the calls were read and hold no written
marker. `suite=` splits a failing acceptance suite by its log into
`does_not_compile(<code>x<error lines>,...; missing <symbols>)` and `tests_failed(<failed> of
<total>)`; plain `failed` is a non-zero exit its log explains neither way, and
`did_not_finish` a suite that timed out, could not start or was not placed.

Do not judge a variant from transcripts (the design's reason for this skill), do not run arms in
parallel (serial interleaved arms isolate CPU, quota and the prompt cache; the design's
measured reason), and do not edit the sealed inputs mid-run: `run` refuses
them. The paid arm is started by the user in their own terminal, never from a tool call: hand them
`python3 <this skill's dir>/scripts/abtest.py run <run_dir>` after a clean `--dry-run`.

## Designing the grid

- **A rewrite needs its source as an arm.** When the variants are your rewrites of ideas taken
  from a source document, add one arm that delivers the source document verbatim: a `[[variant]]`
  whose `dir` holds a `SKILL.md` made of the shipped frontmatter and that document, unchanged
  (the overlay replaces the shipped file). Without it the grid cannot say whether the rewrite
  helps or hurts. Check the grid for it before `seal`.
- **A bare arm is only a no-skill arm.** A `remove_skill` arm does not stand in for a "dynamic
  workflow" arm: a bare agent never uses the Workflow tool unless its prompt asks, so that
  comparison needs its own arm with a `task_file` that asks. Removing a skill also leaves its
  name in other skills' prose (measured: about 85 files named the executor skill under test), so
  state that confound in `PREREG.md`.
- **A fix round does not converge.** Measured on two arms: a fixer handed the remaining confirmed
  findings raised a 20-item checklist from 2 to 8 to 18 and from 12 to 13 to 19 (single judge
  counts, not code-checked), yet a fresh defect hunt still found 6 to 7 open items per arm, and
  both fixers independently wrote the same new flaw. Run a fresh hunt after every round, record
  which defects each round introduced, and never report a round as converged from the checklist.

## Before and during a live run

- **Size `deadline_s` from the longest expected arm, not the skeleton's 14400.** `run` will not
  start an arm whose deadline outlasts the real login (it pauses before the arm); the CLI login
  lasts about 8 h and refreshes only near its expiry, so a 4 h deadline pauses a run for hours.
  Measured arms took 12 to 42 minutes; 7200 (2 h) is ample. Set it before `seal`: `abtest.toml`
  is frozen there, `run` refuses a committed change to it after the seal as well as an
  uncommitted one, and `seal` does not run twice, so a wrong value then means a new run dir.
- **Commit a `PREREG.md` amendment the moment you write it.** `run` refuses any uncommitted or
  untracked change under the sealed inputs; an amendment left uncommitted stops every later
  `run` call until it is committed.
- **A live run spends the account's usage windows, not only USD.** Measured: one long arm used
  about 7 percentage points of the 7-day window's utilization, and about three long arms filled
  the 5-hour window. A usage-limit notice mid-arm pauses the run and SETS THE ATTEMPT ASIDE: on
  resume that arm starts again from scratch, so a 5-hour hit pays for the arm twice (measured: a
  94-minute attempt discarded). Before the user starts a run, state its weekly cost (long arms
  times about 7 percentage points) and plan no more than two long arms per 5-hour window; the
  stream's `rate_limit_event` records carry the current `five_hour` and `seven_day` utilization
  to size the grid from. `run` has no option to stop after a number of arms: it goes on until a
  usage-limit notice pauses it, so fit the grid to the room left in the windows before the user
  starts it.
- **`--dry-run` is not light.** It skips only the session: every arm still gets its worktree and
  the full floor (the gate and the acceptance suite), which takes minutes per arm and competes for
  CPU with a live arm, so never run it beside one, for this run dir or any other. A killed dry
  run leaves arm dirs, branches and a worktree behind; the next `run` sets them aside, and
  `prune-run` removes them.
