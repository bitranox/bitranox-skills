---
name: compuse-toolbox
description: Use when about to hand-roll a small one-off shell/Python utility for a recurring computer-use chore - safely finding or killing a process without self-matching pgrep/pkill, running a test/lint gate and acting on its REAL exit status rather than a pipe's, checking git branch/sync/dirty state across repos, finding which copies of a named file across a tree are tracked-and-modified, gitignored, untracked, or outside any repo, scanning for merge-conflict markers, triaging a noisy CI/build log, filtering a JSONL, pulling the last messages from a Claude Code transcript, deciding from a grep whether some text is already present in a set of files, sweeping a repo for every occurrence of something without silently skipping gitignored files, reading a Windows-written log whose text grep cannot find or that prints with spaces between the letters (UTF-16, BOM, or mixed encodings), retyping an `ssh -i key -o ...` one-liner per call and an scp whose login user has to go inside the path, or checking by eye whether an old and a new version of something behave the same on the same inputs (or whether a hand-rolled detector ever actually says they differ), or picking the latest backup/log/snapshot by eye or with `ls <glob> | sort | tail -1` - which picks the WRONG one whenever a longer name shares the same date prefix as a shorter, newer one, or asking whether a RED/baseline test could ever have failed at all - a scenario whose lesson is already documented elsewhere, or that gives away its own answer, looks exactly like a good result, or hunting with `du` and `rm -rf` for the disk space a deleted git worktree never gave back, because removing the worktree leaves its per-topic build cache sitting outside the checkout where nothing lists it, or hand-rolling a script that splits a tree of CLAUDE.md files into `## ` sections, hashes and groups them, and finds the true common-ancestor directory of a duplicated one before lifting it there. Check these tested jigs first instead of writing throwaway code.
---

# compuse-toolbox

A small set of tested Python jigs for recurring computer-use chores. Reach for one BEFORE
hand-rolling a throwaway `pgrep`/`awk`/`jq`/`json.loads` one-liner - the jig has already handled the
edge cases (self-match, exit-code traps, wrapper argv) that the one-liner gets wrong.

Each jig is a self-contained PEP 723 script: run it with `uv run` (uv provisions its deps), and get
its full arguments from `--help`. Run from the skill directory, or give the full path.

## Tools

| Tool                | Use it when you would otherwise hand-roll...                                                                                                                                                                                                                            | Invoke                                                                                                                           |
|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `procsig`           | `pgrep -f` / `pkill -f` - which self-matches the shell running it and can kill your own session                                                                                                                                                                         | `uv run scripts/procsig.py --exe <name> [--kill]`                                                                                |
| `git_state`         | a `git rev-parse` + `git status` branch/sync/dirty check before a risky commit or bulk op; or "which copies of this file across a tree are tracked-and-modified, gitignored, untracked, or outside any repo?"                                                           | `uv run scripts/git_state.py [REPO ...] [--root DIR]` / `--files CLAUDE.md --root DIR [--json]`                                  |
| `conflict_scan`     | a `grep -rn '^<<<<<<<'` sweep for merge-conflict markers with file:line                                                                                                                                                                                                 | `uv run scripts/conflict_scan.py [PATH ...]`                                                                                     |
| `ci_triage`         | piping a build/CI log through `grep`/`sed`/`awk` to find the error lines                                                                                                                                                                                                | `uv run scripts/ci_triage.py --file LOG [--step ...]`                                                                            |
| `jsonl_grep`        | a `json.loads` loop to filter a JSONL by type/role or extract a field                                                                                                                                                                                                   | `uv run scripts/jsonl_grep.py <file> [--type ...]`                                                                               |
| `transcript_tail`   | parsing a Claude Code transcript JSONL for the last user/assistant text                                                                                                                                                                                                 | `uv run scripts/transcript_tail.py <file> [--role ...]`                                                                          |
| `claim_check`       | a `grep -c` / `grep -l` sweep to decide whether some text is already present in a set of files                                                                                                                                                                          | `uv run scripts/claim_check.py FILE... --pattern P --control C`                                                                  |
| `grep_all`          | a repo-wide `grep -r` that must be COMPLETE - it silently skips gitignored files                                                                                                                                                                                        | `uv run scripts/grep_all.py PATTERN [PATH ...] [--glob G]`                                                                       |
| `gate`              | running gates then acting on the result - `<gate> \| grep summary && git push`                                                                                                                                                                                          | `uv run scripts/gate.py --log L [--summary RE] --gate C [--gate C ...] [--then C]`                                               |
| `winlog`            | `iconv`/`strings -e l` on a WINDOWS log whose text `grep` cannot find, or that `cat`s with spaces between the letters - UTF-16, BOM, or MIXED encodings                                                                                                                 | `uv run scripts/winlog.py read FILE [--grep DONE-OK] [--tail 20] [--json]` (exit 1 = no match)                                   |
| `transfer`          | a `curl --limit-rate` / `rsync --bwlimit` big-file download or host-to-host copy that must respect a REAL speed limit (the units differ per tool: `curl 8M` is 8 MiB/s = 67 Mbit, `rsync --bwlimit` is KiB/s), or judging whether a long job has hung                   | `uv run scripts/transfer.py fetch URL --rate 8Mbit` / `push F user@host:/d/ --rate 8Mbit` / `check --file F --pid N`             |
| `fleet_ssh`         | an `ssh -i <key> -o BatchMode=yes -o ConnectTimeout=N` one-liner retyped per call, or an scp whose login user has to go INSIDE the path (`root@host:/p`) and gets forgotten                                                                                             | `uv run scripts/fleet_ssh.py [--user U] HOST [cmd]` / `--scp SRC DST` (add `--trust-changing-host-keys` for a fleet you reimage) |
| `diffbehave`        | a loop that runs an OLD and a NEW version of a script (or two CLIs meant to be equivalent) on the same inputs and diffs stdout/stderr/exit code by eye - or proving a hand-rolled detector is not a rubber stamp that always says SAME                                  | `uv run scripts/diffbehave.py --a "OLD_CMD" --b "NEW_CMD" --case-file CASES.jsonl` / `--expect-differ N` (known-negative check)  |
| `newest`            | "which backup/log/snapshot is the latest?" answered with `ls <glob> \| sort \| tail -1` - a longer name sharing the same date prefix sorts AFTER a shorter, newer one, so it silently picks the wrong file OR directory                                                 | `uv run scripts/newest.py /backups/nightly-*` / `--all` (every match, newest first) / `--json`                                   |
| `redcheck`          | asking "can this RED/baseline test actually FAIL, or does it only look like it did?" - a scenario whose lesson is already documented elsewhere, or that hands over its own answer, passes for the wrong reason (ships in `process-test-driven-development`, not here)   | `uv run ../process-test-driven-development/scripts/redcheck.py --scenario S.txt --answer A.txt --corpus docs/ --json`            |
| `wtclean`           | `du \| sort -rh` then `rm -rf` hunting for the disk space a DELETED worktree never gave back - `git worktree remove` drops the checkout and leaves its per-topic build cache sitting outside it, gigabytes each, listed by nothing (ships in `git-worktrees`, not here) | `uv run ../git-worktrees/scripts/wtclean.py my-feature` (plan, with sizes) / `my-feature --apply` / `--cache-dir DIR`            |
| `claudemd_variance` | "which `## ` sections are duplicated across my CLAUDE.md files, and where should they live?" - hand-splitting, hashing and grouping them, then guessing the common ancestor instead of computing it (ships in `meta-consolidate-claude-md`, not here)                   | `uv run ../meta-consolidate-claude-md/scripts/claudemd_variance.py --root ~/src` / `--json` / `--min-members 1`                  |

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
- **`fleet_ssh` keeps the key and the login the same identity.** scp carries the login user INSIDE
  the path and has no `--user` flag, so a wrapper that reads `--user` only to pick the key hands
  scp a destination naming nobody: it logs in as the LOCAL user while offering the other user's
  key. On a host that accepts root and refuses your account that is `Permission denied
  (publickey)` from a command line where the flag looks honoured. It also keeps `BatchMode=yes` on
  always, because `-i <key>` alone still falls back to a PASSWORD PROMPT when the key is rejected
  and hangs an unattended run, and it picks a key by READABILITY - a shared key path can exist and
  be root-only on this box, which fails as `Permission denied` with EMPTY stdout far from the
  cause. Host-key checking stays at ssh's strict default; `--trust-changing-host-keys` is the
  opt-in for a fleet you reimage, and it keeps that churn in a separate known-hosts file rather
  than `/dev/null`, which would make every connect a first connect.
- **`git_state --files` cannot conflate tracked-and-ignored.** `git status --porcelain -- <path>`
  is EMPTY for a gitignored file and for a tracked-clean file ALIKE, so a naive per-file check
  reads them as the same thing - and only the tracked one is restorable with `git checkout`.
  `--files` classifies with `git ls-files --error-unmatch` (tracked) and `git check-ignore
  --no-index` (ignored) instead, and asks `check-ignore` only about the paths `ls-files` did NOT
  report tracked - so TRACKED WINS the tracked-and-ignored case deliberately, not by relying on
  git's own default (which happens to also hide tracked files from `check-ignore`, but only
  without `--no-index`). Batches at most 4 git calls PER REPO regardless of file count, never 2
  per file. `git_state`'s repo-state mode reads porcelain v2 (no `rev-parse --short` 2-rev
  footgun).
- **`diffbehave` answers "does this behave differently" by RUNNING both sides, never by reading
  them.** An `ast.dump` diff is identifier-sensitive, so a rename alone reads as a behaviour
  change, and neither a line count nor a `grep -c` executes anything either - none of the three
  can answer the question, only running both sides on the same input and diffing what happened
  can. Its `--expect-differ N` flag is the other half: a hand-rolled detector verified only
  against cases where it already agrees has proved nothing, so the tool fails unless at least N
  cases come back DIFFER - a comparison that can only ever say AGREE is a rubber stamp, not a
  check.
- **`newest` never compares names.** `ls <glob> | sort | tail -1` looks like "the newest" and is
  not: a longer name sharing the same date prefix sorts AFTER a shorter one, so an extra word
  beats the date. Pruning the wrong file this way is loud and gets noticed; VERIFYING against the
  wrong baseline is silent, which is the expensive half. `newest` sorts by mtime only (files and
  directories alike), breaks a genuine tie by input order - deterministic, not directory-listing
  luck - and reports the AGE of what it picked, because the newest member of a stale set is still
  stale and a bare path gives no way to notice that.
- **`redcheck` catches a RED that cannot fail, which reads exactly like one that can.** A
  scenario-based RED (a prompt, not code) fails for two reasons a code RED never has: the agent is
  handed a config cascade and shipped reference material before it ever sees the scenario, so a
  lesson already documented there gets answered from that, not from the scenario; and prose that
  names the trap or pre-diagnoses the cause hands over its own answer. Both make a RED pass for
  the wrong reason with nothing in the transcript to say so. `redcheck` checks a scenario for
  both leaks BEFORE an agent dispatch is spent on it, reporting which corpus document already
  teaches the lesson or which phrase telegraphs the answer. Ships in
  `process-test-driven-development`, indexed here so this table stays the one place that answers
  "is there already a tool for this?".
- **`wtclean` reclaims what removing a worktree leaves behind, which nothing else lists.** A
  per-worktree build cache is deliberately kept OUTSIDE the checkout - that is the point of giving
  each worktree its own - so `git worktree remove` does not touch it and it survives every
  cleanup at gigabytes a time. Nothing enumerates them, so they are normally found by running out
  of disk and then hunting by hand with `du` and `rm -rf`, which is the dangerous way to do it.
  `wtclean` names the worktree and its caches together with sizes, deletes nothing until
  `--apply`, then removes exactly what it listed rather than re-scanning; it refuses a symlinked
  target, a checkout holding uncommitted work, and a topic that is a path rather than a name.
  Ships in `git-worktrees`, indexed here so this table stays the one place that answers "is there
  already a tool for this?".
- **`claudemd_variance` computes a lift target instead of eyeballing one.** Deduplicating
  CLAUDE.md content without checking WHERE it truly belongs is how a false line gets promoted to
  an ancestor that binds every repo below - the common ancestor of a group's member paths is not
  the directory you happened to be looking at, and the common ancestor of a SINGLE file is its own
  parent directory, never the filesystem root. `claudemd_variance` splits every CLAUDE.md into
  `## ` sections, hashes each body (whitespace-normalised, so a reflow does not read as a
  different variant), groups the identical ones, and reports each group's true common ancestor
  plus the largest variant's share - the same "60-75% means one dominant version" signal
  `bitranox:meta-consolidate-claude-md`'s own variance table keys on. It enumerates by a plain
  filesystem WALK and never shells out at all, so - unlike a hand-rolled version built on the
  session's own `grep` - it cannot silently drop a gitignored CLAUDE.md. Ships in
  `meta-consolidate-claude-md`, indexed here so this table stays the one place that answers "is
  there already a tool for this?".
- **The others encode the trap.** `ci_triage` strips ANSI and isolates a step; `jsonl_grep`/
  `transcript_tail` parse JSONL by field, not by fragile text slicing.

## Building or enhancing a jig

Each jig is one import-safe core function plus a thin `argparse` CLI, shipped with a pytest test.
When a jig is insufficient in use, ENHANCE it (add a RED regression test for the gap, then fix),
rather than hand-rolling around it - so the tool matures and cannot silently regress.
