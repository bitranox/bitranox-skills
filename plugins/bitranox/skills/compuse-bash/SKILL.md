---
name: compuse-bash
description: Use when running bash/shell commands and interpreting their exit codes and output - pipelines, chaining a check after a mutating command, process checks with pgrep/pkill, backgrounding, waiting for an event, or when a command "failed" or its result looks ambiguous.
---

# computer-use-bash

Run shell commands so the result is unambiguous, and read that result truthfully.

## Quick reference

| Situation                                   | Rule                                                                                                                                                                                                                                                                                                                 |
|---------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A command exits non-zero                    | NEVER dismiss it as "a quirk". Reproduce the smallest failing form to find the deterministic cause, or fix the command.                                                                                                                                                                                              |
| A command "succeeds" (exit 0)               | Exit 0 is necessary but NOT sufficient. ALSO verify the real artifact/output (file written, content/size correct, options actually applied) - some tools exit 0 while writing nothing or silently ignoring options (e.g. the `vips out.tif[opts]` bracket form). Check the result, not only the status.              |
| Critical command + a check in one call      | Run the mutation in its OWN call (or join with `&&`). A trailing command's exit masks or misattributes the real one.                                                                                                                                                                                                 |
| `cmd \| tail`/`head`/`grep`                 | The pipeline's exit is the LAST stage's, not `cmd`'s. Use `set -o pipefail` or check `${PIPESTATUS[0]}`.                                                                                                                                                                                                             |
| Check/kill a process by name                | `pgrep`/`pkill -f PATTERN` matches your OWN shell. Prefer a pidfile + `kill -0`, a port/unit/cgroup signal, or bracket the first char (`[p]attern`) AND keep the keyword out of `echo` labels in the same command.                                                                                                   |
| Waiting for an event                        | Match the wait to the measured timing plus a small margin; prefer a concrete completion signal over a fixed long sleep.                                                                                                                                                                                              |
| Judging current state from output/logs      | Read the freshest lines and check their timestamps; never conclude from a stale capture.                                                                                                                                                                                                                             |
| Keep / prune the NEWEST timestamped file(s) | Sort by MTIME, not by name: `ls -t` (newest first), or `find DIR -maxdepth 1 -printf '%T@ %p\n' \| sort -zrn`. NEVER rely on plain `ls`/glob order (lexical) - a varying prefix breaks it (`bak-dream-...` sorts before `bak-dreamtest-...`), so the alphabetically-last STALE file is kept and a newer one deleted. |

## Why exit codes get misread

A block like `mutate ... ; echo done ; verify` returns ONLY the last command's status. So a failed critical command is hidden by a succeeding trailing command (false success), or a trivial trailing failure makes a successful critical command look failed (false failure) which then gets waved off as "a quirk". Both are real defects. Run the critical command alone (clean, unambiguous status), then verify separately. When you must chain, use `&&` (status reflects the first failure), and for pipelines read `${PIPESTATUS[@]}`.

## Never "quirk" an error

A non-zero exit always has a deterministic cause. Reproduce the smallest failing form and isolate it (for example `git rev-parse --short A B` fails because `--short` abbreviates one revision, a knowable rule, not a quirk). Dismissing the error guarantees the same confusion next time and can hide a real failure.

## Hook

`block-pgrep-self-match` (PreToolUse on Bash) blocks the `pgrep`/`pkill -f` echo-label self-match. It does not replace preferring pidfile/port/unit signals over a name grep.
