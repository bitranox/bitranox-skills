---
name: compuse-git
description: Use when running git - commit, push, tag, rev-parse, marking a hook or script executable, line endings, interactive flags, or when a git command fails confusingly or a committed file ends up non-executable or with CRLF.
---

# computer-use-git

## Quick reference

| Situation                                    | Rule                                                                                                                                                                                                                                                                                                                     |
|----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `git rev-parse --short` with 2+ revs         | Fails `fatal: needed a single commit` (exit 128). `--short` abbreviates ONE revision. Drop `--short` for multiple (full hashes print fine), or call once per rev.                                                                                                                                                        |
| `push`/`commit`/`tag` + a verify in one call | Run the mutation in its own call; a trailing command's exit masks or misattributes it. Don't dismiss the resulting exit as a quirk.                                                                                                                                                                                      |
| Make a hook/script executable                | `chmod +x` is NOT recorded when `core.fileMode=false` - the file clones/installs non-executable and silently fails. Use `git update-index --chmod=+x <file>`; verify `git ls-files -s <file>` shows `100755`.                                                                                                            |
| Did a mode change "take"?                    | `git config core.fileMode` may be `false` (git ignores permission changes). Trust `git ls-files -s`, not `ls -l`.                                                                                                                                                                                                        |
| A module run via an interpreter/launcher     | Does NOT need the exec bit (`100644` is fine); only a directly-invoked file (`./x.sh`, a hook path) needs `100755`.                                                                                                                                                                                                      |
| Line endings                                 | A script committed with CRLF fails at runtime (`#!/usr/bin/env bash\r` -> `bad interpreter: ...^M`; Python shebangs the same). Pin LF with `.gitattributes` (`*.sh text eol=lf`, `*.py text eol=lf`, `* text=auto`); a Windows checkout or `core.autocrlf=true` reintroduces CRLF.                                       |
| Interactive flags                            | `-i` (`rebase -i`, `add -i`) is unsupported in a non-interactive agent shell. Use non-interactive forms (`rebase --onto`, `commit --fixup` + `rebase --autosquash`, scripted edits).                                                                                                                                     |
| Local build artifacts (`.venv`, caches)      | NEVER track per-machine artifacts: `.venv/`, `__pycache__/`, `*.pyc`, `*.egg-info/`, `node_modules/`, `dist/`, `build/`, `.pytest_cache/`. Tool-agnostic (a `.venv` from `python -m venv`/`virtualenv`/`poetry`/`uv` is equally off-limits). Gitignore them; if already tracked, `git rm -r --cached <path>`. See below. |
| Private repo with private git deps in CI     | The runner cannot read the OTHER private repos -> install fails `could not read Username for 'https://github.com'`. Give CI a read-only PAT secret + a `url.insteadOf` rewrite; load the token from a password file via stdin, never echo it. See below.                                                                 |

## Exec bit + fileMode (the silent hook failure)

When `core.fileMode=false` (common), git ignores working-tree permission bits, so `chmod +x hook.sh` is a no-op in the index: the committed file stays `100644`, and whoever clones or installs it gets a non-executable hook that never runs. Set the bit in the index and verify:

```bash
git update-index --chmod=+x path/to/hook.sh
git ls-files -s path/to/hook.sh   # 100755 = executable in git
```

## Confusing failures are deterministic

A git command that "fails confusingly" has a knowable cause; reproduce the minimal form rather than waving it off. `git rev-parse --short A B` is the canonical example: it always fails because `--short` takes a single revision.

## Don't track local build artifacts

Per-machine, regenerable artifacts must never be committed - they carry absolute paths and platform
binaries that break on every other machine and bloat the repo. This is TOOL-AGNOSTIC: a `.venv/` from
`python -m venv`, `virtualenv`, `poetry`, or `uv` is equally off-limits, as are `__pycache__/`, `*.pyc`,
`*.egg-info/`, `node_modules/`, `dist/`, `build/`, `.pytest_cache/`, and coverage files. Keep them out of
git, and untrack any that slipped in (without deleting the working copy):

```bash
git check-ignore -q .venv || printf '%s\n' '.venv/' '__pycache__/' '*.pyc' '*.egg-info/' >> .gitignore
git ls-files --error-unmatch .venv >/dev/null 2>&1 && git rm -r --cached .venv   # untrack if committed
```

A file already tracked is NOT covered by `.gitignore` until you `git rm --cached` it - gitignore only
stops UNtracked files from being added.

## Private git deps in CI need a read-only token

A private repo that depends on OTHER private repos (`git+https://github.com/<Org>/<repo>` in its
requirements) builds fine locally but fails in CI: the GitHub Actions runner has no read access to those
other private repos, so dependency install dies with `could not read Username for 'https://github.com'`.

The fix is a **read-only token + a git URL rewrite**, with the token loaded so it never reaches the
model or a command line:

1. **Get a read-only PAT into CI as a secret.** The user creates a fine-grained GitHub PAT with only
   `contents: read` on the needed org/repos. They keep it in a **password file** (the agent never reads
   or echoes the literal). Set it as an Actions secret by streaming the file via STDIN:
   ```bash
   # token stays out of argv / ps / scrollback - read in-process, piped to gh on stdin
   python3 -c "import pathlib,subprocess as s; \
   t=pathlib.Path('<creds-dir>/<org>_readonly.token').read_text().strip(); \
   s.run(['gh','secret','set','GIT_PRIVATE_TOKEN_<Org>'],input='<Org>@'+t,text=True,check=True)"
   ```
2. **Where the password files live:** ASK the user for the directory that holds their credential/password
   files (they usually keep them all in ONE place) and look there first; if the file is not there, ASK
   them to create it. Never inline, invent, or hard-code the token, and never print it.
3. **Make CI use it.** If the workflow template already auto-rewrites from a secret convention (e.g. a
   `GIT_PRIVATE_TOKEN_<Org>` secret valued `<Org>@<pat>`), just setting that secret is enough - do not
   hand-edit a template-managed workflow. Otherwise add a rewrite step before the install, one per org:
   ```yaml
   - run: git config --global url."https://${GIT_TOKEN}@github.com/<Org>/".insteadOf "https://github.com/<Org>/"
     env:
       GIT_TOKEN: ${{ secrets.GIT_PRIVATE_TOKEN }}   # the read-only PAT, never the literal in YAML
   ```

A freshly created private repo with private git deps needs this BEFORE its first green CI / release.
(See the global no-secrets rule: load secrets from a keyfile via stdin/env, never echo the literal.)

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

`repo-gate` (PreToolUse on Bash, and `--ci`) blocks a commit on a failing gate (tests-exist, pytest, JSON valid, LF endings, the meta-using-bitranox-skills index in sync, and no leaked secrets/private data). `git-footgun-guard` blocks the always-broken `git rev-parse --short <2+ revs>` before it produces the confusing error.
