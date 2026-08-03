---
name: compuse-toolbox
description: Use when about to hand-roll a small one-off shell/Python utility for a recurring computer-use chore - safely finding or killing a process without self-matching pgrep/pkill, running a test/lint gate and acting on its REAL exit status rather than a pipe's, checking git branch/sync/dirty state across repos, scanning for merge-conflict markers, triaging a noisy CI/build log, filtering a JSONL, pulling the last messages from a Claude Code transcript, deciding from a grep whether some text is already present in a set of files, sweeping a repo for every occurrence of something without silently skipping gitignored files, or reading a Windows-written log whose text grep cannot find or that prints with spaces between the letters (UTF-16, BOM, or mixed encodings). Check these tested jigs first instead of writing throwaway code.
---

# compuse-toolbox

A small set of tested Python jigs for recurring computer-use chores. Reach for one BEFORE
hand-rolling a throwaway `pgrep`/`awk`/`jq`/`json.loads` one-liner - the jig has already handled the
edge cases (self-match, exit-code traps, wrapper argv) that the one-liner gets wrong.

Each jig is a self-contained PEP 723 script: run it with `uv run` (uv provisions its deps), and get
its full arguments from `--help`. Run from the skill directory, or give the full path.

## Tools

| Tool              | Use it when you would otherwise hand-roll...                                                                                                            | Invoke                                                                                         |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `procsig`         | `pgrep -f` / `pkill -f` - which self-matches the shell running it and can kill your own session                                                         | `uv run scripts/procsig.py --exe <name> [--kill]`                                              |
| `git_state`       | a `git rev-parse` + `git status` branch/sync/dirty check before a risky commit or bulk op                                                               | `uv run scripts/git_state.py [REPO ...] [--root DIR]`                                          |
| `conflict_scan`   | a `grep -rn '^<<<<<<<'` sweep for merge-conflict markers with file:line                                                                                 | `uv run scripts/conflict_scan.py [PATH ...]`                                                   |
| `ci_triage`       | piping a build/CI log through `grep`/`sed`/`awk` to find the error lines                                                                                | `uv run scripts/ci_triage.py --file LOG [--step ...]`                                          |
| `jsonl_grep`      | a `json.loads` loop to filter a JSONL by type/role or extract a field                                                                                   | `uv run scripts/jsonl_grep.py <file> [--type ...]`                                             |
| `transcript_tail` | parsing a Claude Code transcript JSONL for the last user/assistant text                                                                                 | `uv run scripts/transcript_tail.py <file> [--role ...]`                                        |
| `claim_check`     | a `grep -c` / `grep -l` sweep to decide whether some text is already present in a set of files                                                          | `uv run scripts/claim_check.py FILE... --pattern P --control C`                                |
| `grep_all`        | a repo-wide `grep -r` that must be COMPLETE - it silently skips gitignored files                                                                        | `uv run scripts/grep_all.py PATTERN [PATH ...] [--glob G]`                                     |
| `gate`            | running gates then acting on the result - `<gate> \| grep summary && git push`                                                                          | `uv run scripts/gate.py --log L [--summary RE] --gate C [--gate C ...] [--then C]`             |
| `winlog`          | `iconv`/`strings -e l` on a WINDOWS log whose text `grep` cannot find, or that `cat`s with spaces between the letters - UTF-16, BOM, or MIXED encodings | `uv run scripts/winlog.py read FILE [--grep DONE-OK] [--tail 20] [--json]` (exit 1 = no match) |

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
- **`gate` reports the gate's OWN exit status, never a pipe's.** `<gate> | grep summary && git push`
  exits with `grep`'s status, so a red gate whose log still holds a green-looking line reads as
  success and the `&&` fires; writing `rc=$?` after the pipe records the same wrong status. `gate`
  runs each command with no shell and no pipe, so `returncode` is the gate's, sends output to a log,
  and greps the summary from that log AFTERWARDS - then runs `--then` only on a real pass. The
  plugin already BLOCKS the masked form (`hooks/block-masked-gate-exit.py`); this is the safe form
  to reach for instead of hand-rolling per-gate `rc=$?` capture and temp files each time.
  Launch this one with plain `python3`, not `uv run`: it declares no dependencies, and `uv run`
  puts its own ephemeral interpreter on the environment the CHILD gates inherit - measured, a gate
  shelling out to `python3 -m pytest` then died with `No module named pytest` and reported a false
  RED. Every other jig here is fine under `uv run`; only this one runs other commands.
- **`winlog` decodes a Windows log per SEGMENT, because one file can hold two encodings.**
  PowerShell writes UTF-16 from `Tee-Object`/`Out-File` but UTF-8 or ANSI from `Set-Content`, so a
  log created by one and appended to by the other is MIXED - with no BOM to announce it. Nothing
  errors: `grep` just finds nothing and `cat` prints `D O N E - O K`. A wait loop keyed on that
  marker then reports "not finished" for a run that finished, and times out on SUCCESS exactly as
  it would on failure. `iconv -f UTF-16LE` is not the fix: on a real mixed log it decoded the
  UTF-16 tail fine, exited 0, and silently turned the ASCII head into CJK mojibake - the header
  and the `running as NT-AUTORITAET\SYSTEM` line, which was the evidence that the task ran
  elevated. Partial, silent, and reported as success. `file` calls such a log plain `data`, so it
  will not even confirm the diagnosis. `winlog` decodes each segment on its own, keeps both halves
  (umlauts included), normalizes CRLF, and prints what it found on stderr - naming a MIXED file so
  it gets fixed at the WRITER instead of worked around in every reader.
- **The others encode the trap.** `git_state` reads porcelain v2 (no `rev-parse --short` 2-rev
  footgun); `ci_triage` strips ANSI and isolates a step; `jsonl_grep`/`transcript_tail` parse JSONL
  by field, not by fragile text slicing.

## Building or enhancing a jig

Each jig is one import-safe core function plus a thin `argparse` CLI, shipped with a pytest test.
When a jig is insufficient in use, ENHANCE it (add a RED regression test for the gap, then fix),
rather than hand-rolling around it - so the tool matures and cannot silently regress.
