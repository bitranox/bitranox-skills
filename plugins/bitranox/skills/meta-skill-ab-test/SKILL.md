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

| Subcommand  | One line                                                                                        |
|-------------|-------------------------------------------------------------------------------------------------|
| `init`      | writes `abtest.toml` (the profile), `task.md` and `PREREG.md` skeletons into a new run dir       |
| `seal`      | validates them, records the acceptance suite's hash and commits them; the inputs are frozen     |
| `run`       | the serial interleaved arms (`--dry-run` first, `--only C` for one arm); resumes from its journal |
| `score`     | per-arm cost from the stream, floor result, void rules and store-change flags                   |
| `prune-run` | deletes the run's branches, worktrees and hook dirs in the workpiece; leaves nothing of the run |

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
branches and keeps the run dir.

Do not judge a variant from transcripts (the design's reason for this skill), do not run arms in
parallel (serial interleaved arms isolate CPU, quota and the prompt cache; the design's
measured reason), and do not edit the sealed inputs mid-run: `run` refuses
them. The paid arm is started by the user in their own terminal, never from a tool call: hand them
`python3 <this skill's dir>/scripts/abtest.py run <run_dir>` after a clean `--dry-run`.
