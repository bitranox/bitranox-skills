---
name: computer-use-git
description: Use when running git - commit, push, tag, rev-parse, marking a hook or script executable, line endings, interactive flags, or when a git command fails confusingly or a committed file ends up non-executable or with CRLF.
---

# computer-use-git

## Quick reference

| Situation | Rule |
|-----------|------|
| `git rev-parse --short` with 2+ revs | Fails `fatal: needed a single commit` (exit 128). `--short` abbreviates ONE revision. Drop `--short` for multiple (full hashes print fine), or call once per rev. |
| `push`/`commit`/`tag` + a verify in one call | Run the mutation in its own call; a trailing command's exit masks or misattributes it. Don't dismiss the resulting exit as a quirk. |
| Make a hook/script executable | `chmod +x` is NOT recorded when `core.fileMode=false` - the file clones/installs non-executable and silently fails. Use `git update-index --chmod=+x <file>`; verify `git ls-files -s <file>` shows `100755`. |
| Did a mode change "take"? | `git config core.fileMode` may be `false` (git ignores permission changes). Trust `git ls-files -s`, not `ls -l`. |
| A module run via an interpreter/launcher | Does NOT need the exec bit (`100644` is fine); only a directly-invoked file (`./x.sh`, a hook path) needs `100755`. |
| Line endings | A script committed with CRLF fails at runtime (`#!/usr/bin/env bash\r` -> `bad interpreter: ...^M`; Python shebangs the same). Pin LF with `.gitattributes` (`*.sh text eol=lf`, `*.py text eol=lf`, `* text=auto`); a Windows checkout or `core.autocrlf=true` reintroduces CRLF. |
| Interactive flags | `-i` (`rebase -i`, `add -i`) is unsupported in a non-interactive agent shell. Use non-interactive forms (`rebase --onto`, `commit --fixup` + `rebase --autosquash`, scripted edits). |

## Exec bit + fileMode (the silent hook failure)

When `core.fileMode=false` (common), git ignores working-tree permission bits, so `chmod +x hook.sh` is a no-op in the index: the committed file stays `100644`, and whoever clones or installs it gets a non-executable hook that never runs. Set the bit in the index and verify:

```bash
git update-index --chmod=+x path/to/hook.sh
git ls-files -s path/to/hook.sh   # 100755 = executable in git
```

## Confusing failures are deterministic

A git command that "fails confusingly" has a knowable cause; reproduce the minimal form rather than waving it off. `git rev-parse --short A B` is the canonical example: it always fails because `--short` takes a single revision.

## Hooks

`repo-gate` (PreToolUse on Bash, and `--ci`) blocks a commit on a failing gate (tests-exist, pytest, JSON valid, LF endings, the using-bitranox-skills index in sync, and no leaked secrets/private data). `git-footgun-guard` blocks the always-broken `git rev-parse --short <2+ revs>` before it produces the confusing error.
