---
name: computer-use-git
description: Use when running git - commit, push, tag, rev-parse, marking a hook or script executable, line endings, interactive flags, or when a git command fails confusingly or a committed file ends up non-executable or with CRLF.
---

# computer-use-git

## Quick reference

| Situation                                    | Rule                                                                                                                                                                                                                                                                               |
|----------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `git rev-parse --short` with 2+ revs         | Fails `fatal: needed a single commit` (exit 128). `--short` abbreviates ONE revision. Drop `--short` for multiple (full hashes print fine), or call once per rev.                                                                                                                  |
| `push`/`commit`/`tag` + a verify in one call | Run the mutation in its own call; a trailing command's exit masks or misattributes it. Don't dismiss the resulting exit as a quirk.                                                                                                                                                |
| Make a hook/script executable                | `chmod +x` is NOT recorded when `core.fileMode=false` - the file clones/installs non-executable and silently fails. Use `git update-index --chmod=+x <file>`; verify `git ls-files -s <file>` shows `100755`.                                                                      |
| Did a mode change "take"?                    | `git config core.fileMode` may be `false` (git ignores permission changes). Trust `git ls-files -s`, not `ls -l`.                                                                                                                                                                  |
| A module run via an interpreter/launcher     | Does NOT need the exec bit (`100644` is fine); only a directly-invoked file (`./x.sh`, a hook path) needs `100755`.                                                                                                                                                                |
| Line endings                                 | A script committed with CRLF fails at runtime (`#!/usr/bin/env bash\r` -> `bad interpreter: ...^M`; Python shebangs the same). Pin LF with `.gitattributes` (`*.sh text eol=lf`, `*.py text eol=lf`, `* text=auto`); a Windows checkout or `core.autocrlf=true` reintroduces CRLF. |
| Interactive flags                            | `-i` (`rebase -i`, `add -i`) is unsupported in a non-interactive agent shell. Use non-interactive forms (`rebase --onto`, `commit --fixup` + `rebase --autosquash`, scripted edits).                                                                                               |

## Exec bit + fileMode (the silent hook failure)

When `core.fileMode=false` (common), git ignores working-tree permission bits, so `chmod +x hook.sh` is a no-op in the index: the committed file stays `100644`, and whoever clones or installs it gets a non-executable hook that never runs. Set the bit in the index and verify:

```bash
git update-index --chmod=+x path/to/hook.sh
git ls-files -s path/to/hook.sh   # 100755 = executable in git
```

## Confusing failures are deterministic

A git command that "fails confusingly" has a knowable cause; reproduce the minimal form rather than waving it off. `git rev-parse --short A B` is the canonical example: it always fails because `--short` takes a single revision.

## Before you push / PR / publish: review for leaked data

A push, PR, or publish is irreversible exposure on a shared or public remote - and even after you
delete a value it stays in history (removing it needs a force-push, which breaks existing clones).
So before `git push` / `gh pr create` / a release, review what will ACTUALLY leave the machine.

- **Review the whole push range, not just the last diff.** `git push` sends EVERY unpushed commit on
  the branch (and `--all`/`--tags`/`--mirror`, or pushing a side branch, sends even more), so a
  secret committed three commits ago still goes out. Scan the range, not `git diff --cached`:
  `git diff @{push}..HEAD` (or `git diff <base>...HEAD` for a PR), plus `git log --stat <range>`.
- **What to look for:** secrets/credentials (API keys, tokens, passwords, private keys,
  `.env`/`id_rsa`/`*.pem`), private infrastructure (internal hostnames, private IPs, internal
  URLs/paths, host/cluster names), and personal data (emails, names). Quick grep:
  `git diff @{push}..HEAD | grep -inE 'api[_-]?key|secret|token|password|BEGIN .*PRIVATE KEY'`.
- **Use documentation-safe placeholders** in examples: `example.com`/`example.test` for domains and
  the RFC5737 ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) for IPs.
- A deterministic secret/denylist gate (pre-commit / CI) catches the unambiguous cases, but the
  judgement call - a real internal IP vs a generic example - is yours. Do it BEFORE the push.

## Hooks

`repo-gate` (PreToolUse on Bash, and `--ci`) blocks a commit on a failing gate (tests-exist, pytest, JSON valid, LF endings, the using-bitranox-skills index in sync, and no leaked secrets/private data). `git-footgun-guard` blocks the always-broken `git rev-parse --short <2+ revs>` before it produces the confusing error.
