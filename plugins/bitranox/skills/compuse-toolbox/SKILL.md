---
name: compuse-toolbox
description: Use when about to hand-roll a small one-off shell/Python utility for a recurring computer-use chore - safely finding or killing a process without self-matching pgrep/pkill, checking git branch/sync/dirty state across repos, scanning for merge-conflict markers, triaging a noisy CI/build log, filtering a JSONL, pulling the last messages from a Claude Code transcript, deciding from a grep whether some text is already present in a set of files, or sweeping a repo for every occurrence of something without silently skipping gitignored files. Check these tested jigs first instead of writing throwaway code.
---

# compuse-toolbox

A small set of tested Python jigs for recurring computer-use chores. Reach for one BEFORE
hand-rolling a throwaway `pgrep`/`awk`/`jq`/`json.loads` one-liner - the jig has already handled the
edge cases (self-match, exit-code traps, wrapper argv) that the one-liner gets wrong.

Each jig is a self-contained PEP 723 script: run it with `uv run` (uv provisions its deps), and get
its full arguments from `--help`. Run from the skill directory, or give the full path.

## Tools

| Tool              | Use it when you would otherwise hand-roll...                                                    | Invoke                                                          |
|-------------------|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| `procsig`         | `pgrep -f` / `pkill -f` - which self-matches the shell running it and can kill your own session | `uv run scripts/procsig.py --exe <name> [--kill]`               |
| `git_state`       | a `git rev-parse` + `git status` branch/sync/dirty check before a risky commit or bulk op       | `uv run scripts/git_state.py [REPO ...] [--root DIR]`           |
| `conflict_scan`   | a `grep -rn '^<<<<<<<'` sweep for merge-conflict markers with file:line                         | `uv run scripts/conflict_scan.py [PATH ...]`                    |
| `ci_triage`       | piping a build/CI log through `grep`/`sed`/`awk` to find the error lines                        | `uv run scripts/ci_triage.py --file LOG [--step ...]`           |
| `jsonl_grep`      | a `json.loads` loop to filter a JSONL by type/role or extract a field                           | `uv run scripts/jsonl_grep.py <file> [--type ...]`              |
| `transcript_tail` | parsing a Claude Code transcript JSONL for the last user/assistant text                         | `uv run scripts/transcript_tail.py <file> [--role ...]`         |
| `claim_check`     | a `grep -c` / `grep -l` sweep to decide whether some text is already present in a set of files  | `uv run scripts/claim_check.py FILE... --pattern P --control C` |
| `grep_all`        | a repo-wide `grep -r` that must be COMPLETE - it silently skips gitignored files | `uv run scripts/grep_all.py PATTERN [PATH ...] [--glob G]` |

Per-tool arguments live in each tool's `--help` (loaded only when used, so this index stays small).

## Why a jig over a one-liner

- **`procsig` cannot self-match.** It reads `/proc` directly and always excludes its own process and
  every ancestor, so it structurally cannot signal the shell that launched it - the failure mode
  `pkill -f X` has whenever the shell's own command line contains `X`.
- **`procsig --cmdline` also never searches a command STRING a shell was handed.** Exclusion covers
  only self and ancestors, and a SIBLING shell quoting the needle is neither: one such match killed
  a live command mid-run. So `bash -c '<text>'` and every equivalent is searched only up to the flag
  that introduces the string, and an argv that MIGHT hold one but cannot be classified with
  certainty is skipped entirely rather than assumed harmless. The bias is deliberate and one-way - a
  miss costs you one `kill <pid>`, a false match kills the wrong process - so if an expected process
  is absent from the listing, match it with `--exe` or `--comm`. Full rules in the tool's `--help`.
- **`claim_check` refuses to answer "no" blindly.** A content check's dangerous result is the
  NEGATIVE, because "not present" and "I never really looked" print the same. So every query carries
  a CONTROL pattern that MUST match; if the control misses, the verdict is BROKEN (exit 2), not
  ABSENT (exit 1), and no answer is given. That converts a silent false all-clear into a loud
  failure - the exact shape behind a `grep -c` whose `file:count` output was never parsed, and a
  threshold set above the whole distribution so no pair could ever match.
- **`grep_all` cannot silently under-report.** In a Claude Code session `grep` routes to a
  gitignore-aware backend, so a repo-wide sweep drops ignored files and the miss reads as a
  clean result. `grep_all` walks the filesystem itself and then reports how many of its hits
  git considers ignored, which is exactly the number a normal grep would have missed. Measured
  on this tree: 73 pointer blocks found, 55 of them gitignored, against 17 from the session
  grep. A zero in that stderr line means the two agree and your earlier grep was safe.
- **The others encode the trap.** `git_state` reads porcelain v2 (no `rev-parse --short` 2-rev
  footgun); `ci_triage` strips ANSI and isolates a step; `jsonl_grep`/`transcript_tail` parse JSONL
  by field, not by fragile text slicing.

## Building or enhancing a jig

Each jig is one import-safe core function plus a thin `argparse` CLI, shipped with a pytest test.
When a jig is insufficient in use, ENHANCE it (add a RED regression test for the gap, then fix),
rather than hand-rolling around it - so the tool matures and cannot silently regress.
