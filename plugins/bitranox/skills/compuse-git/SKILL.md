---
name: compuse-git
description: Use when running git - commit, push, tag, rev-parse, marking a hook or script executable, line endings, interactive flags, or when a git command fails confusingly or a committed file ends up non-executable or with CRLF.
---

# computer-use-git

## Quick reference

| Situation                                             | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|-------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `git rev-parse --short` with 2+ revs                  | Fails `fatal: Needed a single revision` (exit 128). That text is LOCALIZED - on a non-English machine it comes back translated, so detect this by the exit code, never by grepping the message. `--short` abbreviates ONE revision. Drop `--short` for multiple (full hashes print fine), or call once per rev.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Testing whether a ref EXISTS                          | `git rev-parse <missing-ref>` ECHOES THE NAME BACK on stdout (the error goes only to stderr, exit is non-zero), so `$(git rev-parse X)` captured into a variable holds the literal string `X` and an equality test reports a confident FALSE result. Use `git rev-parse --verify -q <ref>`, which prints nothing and exits non-zero. Never hide the miss with `2>/dev/null` and compare anyway.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| A bare `git` after an earlier `cd`                    | The Bash tool's cwd PERSISTS between calls, so a bare `git` answers from whatever repo you last `cd`'d into - a per-repo loop written as `cd "$r" && git ...` silently reports one repo's state for another when a `cd` fails. This holds between calls of ONE message too: a call that WRITES (commit, push, `make test`) runs after the call before it has finished and starts where that call left the shell, so `cd /a && git commit ...` in one call moves a bare `git commit` in the next; read-only calls run side by side and do not see each other's `cd`. Pass `-C <repo>` on every invocation instead of `cd`, and sanity-check a sweep's result count against the repo count. `block-write-after-sibling-cd` refuses the same-message shape: a repo-writing call with no absolute target of its own (`cd /abs`, `git -C /abs`, `make -C /abs`) after an earlier call of that message changed directory. Nothing refuses the cross-message shape: `git-wrong-repo-nudge` reads ONE call at a time, and an arm firing on any cd-less `git` was measured at 4.499% of 65,810 real commands - one in 22, against the shipped arm's 0.186% - and rejected as noise. There the discipline is yours to keep, not the guard's. |
| `rerere` replaying a recorded resolution              | With `rerere.autoUpdate` on it can SILENTLY replay a stale resolution onto a NON-conflicted hunk, so code is dropped or mangled while the tree still compiles and the whole suite passes. A green build is not evidence here. Verify by a content invariant (grep the expected symbol/count), and review what it touched: `git rerere status`, `git rerere diff`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Will a stale branch still merge cleanly?              | `git merge-tree --write-tree <target> <branch>` (git 2.38+) with both branch TIPS - it finds the merge base itself; passing the base as the first argument always reads as clean. It changes NO ref, index or working tree: it writes the merge into the object store and prints the merged TREE sha, exiting 1 on a conflict with the conflicted paths listed after that sha, whose tree then holds conflict markers. Prefer it to a scratch worktree or a `--no-commit` merge, which both touch the checkout. A clean trial merge proves only that there is no TEXTUAL conflict and is not a green gate: inspect the result (`git grep <pattern> <tree-sha>`, `git ls-tree <tree-sha>`) and run the project's test gate on the real merge before anyone calls it done.                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Is a `git clone` finished? / `.git/index.lock` exists | `git rev-parse HEAD` and the existence of `.git/` turn true while the clone is still checking out: the refs are written before the worktree, so both answer YES over an empty or half-written tree (`git status` there lists tracked paths as deleted). Wait on the clone PROCESS instead: run it as a tracked background task and wait for its completion, or poll `kill -0 <pid>`; if you must judge from the filesystem, test a path the checkout writes LAST. The running clone also holds `.git/index.lock`, so a command started too early fails on git's lock message, which is written for a crashed process and suggests removing the file. Before removing any `.git/*.lock`, require that no live git process is working in that repo; if one is, wait - deleting the lock under it can corrupt the clone.                                                                                                                                                                                                                                                                                                                                                                                                              |
| Undoing an experimental edit to a file                | `git checkout -- <file>` restores from the INDEX or HEAD, so it discards EVERY uncommitted change in that file, not only the experiment you meant to undo. When the file also holds work in progress - a feature mid-cycle, an edit made to prove a test can fail - copy it aside BEFORE editing and restore from that copy. The loss is silent in the direction that looks like success: the file drops out of `git status`, which reads as clean. Git is a correct restore only for work already committed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `git rm --cached` refuses an `AM`/`MM` file           | It exits 1 with `error: the following file has staged content different from both the file and the HEAD` (text under `LC_ALL=C`; localized otherwise, so key on the `AM`/`MM` status, not the message). The INDEX then holds a version that exists nowhere else - not in HEAD, not on disk - and the `-f` git suggests drops the only reference to it while the working-tree copy survives: it lingers as an unreachable blob, findable only through `git fsck --unreachable`, until `git gc` prunes it. Save it first: `git show :<file> > <copy>`, then `git rm -f --cached <file>`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Pull/merge/checkout that ADDS a path you have ignored | Git overwrites the ignored local file with exit 0 and no output (a non-ignored one blocks). Before pulling: `git diff --name-only --diff-filter=A HEAD..@{upstream} \| git check-ignore -v --stdin`, back up each hit. See below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `push`/`commit`/`tag` + a verify in one call          | Run the mutation in its own call; a trailing command's exit masks or misattributes it. Don't dismiss the resulting exit as a quirk.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Chain a quality gate before `commit`/`push`           | Join the gate and the commit with `&&` so a RED gate BLOCKS the commit (`pytest && git commit ...`). A newline- or `;`-separated sequence runs the commit REGARDLESS of the gate's exit status and pushes a red state. (Different failure from reading a gate's rc out of a compound background job - here the `;` simply discards the gate's exit.)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Make a hook/script executable                         | `chmod +x` is NOT recorded when `core.fileMode=false` - the file clones/installs non-executable and silently fails. Use `git update-index --chmod=+x <file>`; verify `git ls-files -s <file>` shows `100755`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Did a mode change "take"?                             | `git config core.fileMode` may be `false` (git ignores permission changes). Trust `git ls-files -s`, not `ls -l`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| A module run via an interpreter/launcher              | Does NOT need the exec bit (`100644` is fine); only a directly-invoked file (`./x.sh`, a hook path) needs `100755`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Line endings                                          | A script committed with CRLF fails at runtime (`#!/usr/bin/env bash\r` -> `bad interpreter: ...^M`; Python shebangs the same). Pin LF with `.gitattributes` (`*.sh text eol=lf`, `*.py text eol=lf`, `* text=auto`); a Windows checkout or `core.autocrlf=true` reintroduces CRLF. A whole file modified after a Windows save: see "Line-ending churn after a Windows save" below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Interactive flags                                     | `-i` (`rebase -i`, `add -i`) is unsupported in a non-interactive agent shell. Use non-interactive forms (`rebase --onto`, `commit --fixup` + `rebase --autosquash`, scripted edits).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Local build artifacts (`.venv`, caches)               | NEVER track per-machine artifacts: `.venv/`, `__pycache__/`, `*.pyc`, `*.egg-info/`, `node_modules/`, `dist/`, `build/`, `.pytest_cache/`. Tool-agnostic (a `.venv` from `python -m venv`/`virtualenv`/`poetry`/`uv` is equally off-limits). Gitignore them; if already tracked, `git rm -r --cached <path>`. See below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Private repo with private git deps in CI              | The runner cannot read the OTHER private repos -> install fails `could not read Username for 'https://github.com'`. Give CI a read-only PAT secret + a `url.insteadOf` rewrite; load the token from a password file via stdin, never echo it. See below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Multiple agents/sessions share one checkout           | Branch/HEAD/index can change UNDER you between reads, so a commit lands on the wrong branch or a stale base. Before committing: verify `git branch --show-current`, check `git rev-list --left-right --count HEAD...@{upstream}` (behind/diverged = origin advanced), and stage only YOUR files (never `git add -A`). Durable fix: a `git worktree` per session. See below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `for-each-ref`/`tag` with 2+ `--sort` keys            | The LAST `--sort` key is PRIMARY, so left-to-right reads backwards: `--sort=-creatordate --sort=-v:refname` sorts by VERSION first and date only breaks a tie. For newest-by-date with a version tiebreak, put `-creatordate` LAST: `--sort=-v:refname --sort=-creatordate`. `-creatordate` alone ties on same-second tags and falls back to ASCENDING refname order regardless of its own `-` prefix. The two orders disagree ONLY when an old tag carries a high version and a new tag a low one (`v10.0.0` tagged before `v2.0.0`) - test that shape, not a monotonically increasing history, where every ordering looks correct. Build that fixture with annotated tags dated by `GIT_COMMITTER_DATE`, which sets their `creatordate`, and comment the two-key line to say the last key is primary, since it otherwise reads as a mistake.                                                                                                                                                                                                                                                                                                                                                                                     |
| Asserting a clean tree with `&& echo CLEAN`           | `git status --porcelain && echo CLEAN` asserts NOTHING: `&&` only means `git status --porcelain` exited 0, which it does whether the tree is dirty or clean - `status` does not use its exit code to report dirtiness. Capture the OUTPUT and test it is empty (`[ -z "$(git status --porcelain)" ]`), and give the check a CONTROL once: deliberately dirty the tree and confirm the same command then reports non-empty, or a passing check could be structurally unable to fail.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `git reset --keep` with another session's staged file | `reset --keep` resets the INDEX to the target commit while trying to preserve worktree differences, but it has no concept of "another session's stage": a file ANOTHER session staged (`git status --porcelain` shows `A`) becomes UNTRACKED (`??`) after the reset, while its on-disk CONTENT survives untouched. Recovery - even if the working copy is later lost too - the blob is already in the object database from the earlier `git add`: find it with `LC_ALL=C git fsck --unreachable` (it prints as a dangling blob) and restore the index entry with `git update-index --add --cacheinfo 100644,<blob-sha>,<path>`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## An incoming file silently overwrites an IGNORED local file

`git pull`, `merge`, `checkout` and `switch` REFUSE when an incoming commit adds a path that exists
locally as a plain untracked file (`untracked working tree files would be overwritten`). They do NOT
refuse when that local file is gitignored: git treats ignored files as disposable, replaces the
content, **exits 0 and prints nothing**. A local `CLAUDE.md`, `.env` or config that a template sync
starts tracking is lost this way, with no stash and no reflog entry. Measured on git 2.53.0: `pull`
(fast-forward), `merge`, `checkout -B` and `switch`, with the ignore rule in `.git/info/exclude`, and
`merge` and `switch` with it in `.gitignore`; `pull --rebase` and a global `core.excludesFile` were
not measured, assume the same. Paths print repo-relative, so a nested hit is `dir/CLAUDE.md`. Run this BEFORE the pull and back up every hit:

```bash
git fetch -q
git diff --name-only --diff-filter=A HEAD..@{upstream} | git check-ignore -v --stdin
```

Each line printed names a path the pull will overwrite if it exists on disk (`-v` adds the ignore
rule). Copy it to a durable place outside the repo (`cp -p <path> ~/<path>.bak-<date>`, not a
session scratch dir) before pulling. After the pull the path is tracked and holds upstream's content:
keep your local content as an untracked file under another name (for `CLAUDE.md`, `CLAUDE.local.md`)
or merge it by hand, never edit the tracked file in place. For a merge, checkout or switch, or a
branch with no upstream, use `HEAD..<incoming-ref>` (e.g. `origin/main`) instead of
`HEAD..@{upstream}`. `check-ignore` exits 1 when nothing matches, so an empty result is safe to
proceed on.

## Exec bit + fileMode (the silent hook failure)

When `core.fileMode=false` (common), git ignores working-tree permission bits, so `chmod +x hook.sh` is a no-op in the index: the committed file stays `100644`, and whoever clones or installs it gets a non-executable hook that never runs. Set the bit in the index and verify:

```bash
git update-index --chmod=+x path/to/hook.sh
git ls-files -s path/to/hook.sh   # 100755 = executable in git
```

## Line-ending churn after a Windows save

A file saved on Windows in a repo with no `.gitattributes` can come back with every line ending
flipped to CRLF: `git status` lists it as modified and `git diff --numstat` reports equal
insertions and deletions (`87 87 f.sh`). Equal N/N also fits a real full rewrite, and a one-line
edit hidden under the churn, so it is the signal, not the proof. Check each file:

```bash
git ls-files --eol f.sh                                       # i/lf w/crlf = worktree copy has CRLF
diff <(git show HEAD:f.sh | tr -d '\r') <(tr -d '\r' < f.sh)  # empty = no real change
```

`git ls-files --eol` names the ending in the index (`i/`) and the worktree (`w/`), never whether
the content changed; the CR-stripped diff answers that, and for a file with a real edit it prints
only the edited lines. Restore every file whose stripped diff is empty with
`git checkout -- <file>` (it discards everything uncommitted in that file, so run it only on
those), and keep the real edit, saved again with LF.

If the churn is already COMMITTED (pushed by a colleague, `git ls-files --eol` shows `i/crlf`),
HEAD holds the CRLF copy, so a diff against HEAD and `git checkout --` both reproduce it. Compare
against the last commit before the churn instead (`<base>` = that commit, often `HEAD~1` or the
merge-base with the main branch): `diff <(git show <base>:f.sh | tr -d '\r') <(tr -d '\r' < f.sh)`
shows the real edit, and the fix is the renormalize commit below, not a checkout.

Then stop it recurring:

- Add the `.gitattributes` from the table row (`*.sh text eol=lf`, `*.py text eol=lf`, ...,
  `* text=auto`). `eol=lf` keeps the checkout LF even under `core.autocrlf=true`; a file matched
  only by `* text=auto` follows the checkout's `core.autocrlf` and still gets CRLF on Windows. A
  catch-all `* text=auto eol=lf` pins everything and is safe only when no `.bat`/`.cmd` is
  tracked: those need CRLF (`*.bat text eol=crlf`, `*.cmd text eol=crlf`).
- A file already committed with CRLF (`i/crlf`) stays that way until you run
  `git add --renormalize .` after the `.gitattributes` change; commit both together.
- Prove it holds on a Windows checkout without a Windows box: after committing, clone with
  `git clone -c core.autocrlf=true <repo> <tmp>` and count CRs in its files (`grep -c $'\r'`);
  every count must be 0. A file that still shows CRs there is one your rules do not pin.

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
       GIT_TOKEN: ${{ secrets.GITHUB_READONLY_PAT_<Org> }}   # a SEPARATE secret holding the RAW PAT (not step 1's <Org>@<pat> value, which is only for the template auto-rewrite); never the literal in YAML
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

## Private tooling in a fork belongs in .git/info/exclude, never a tracked .gitignore

When a checkout pushes to a FOREIGN remote - a fork, an upstream PR branch, anyone else's repo -
keep per-clone tooling (agent instruction files, editor config, scratch notes) out of the TRACKED
`.gitignore`. A tracked ignore line is not protection. It is what makes the file committable: the
private file then sits beside a tracked line asserting it belongs, and the next `git add -A` or
`git commit -a` takes both.

Use `.git/info/exclude` instead. It is per-clone and never pushed, so it removes the file's
ability to be committed rather than relying on a human reading the push range.

**Verify the exclude FIRES rather than merely existing** - `git status --porcelain` must print
nothing while the files are on disk:

```bash
printf '%s\n' CLAUDE.md .claude/ >> .git/info/exclude
git status --porcelain      # must print NOTHING; any line here means the file is still committable
```

If such a commit already exists and is unpushed, `git reset --hard <upstream-ref>` and restore the
files untracked.

## Committing safely when sessions/agents share a checkout

Running more than one agent or session in the SAME working copy (or you alongside an automation) means
the branch, HEAD, index, and uncommitted files can change UNDER you between two reads - one checkout has
no per-session isolation. A commit then lands on the wrong branch, on a stale base, or sweeps in another
session's uncommitted files. Before any commit, verify state (cheap, deterministic):

```bash
git branch --show-current                            # the branch you expect? (not a sibling's, not detached)
git rev-list --left-right --count HEAD...@{upstream}  # "<ahead> <behind>"; behind/diverged = origin advanced
git status --short                                    # any A/M you did not stage? the branch-guard misses those
git commit -m "msg" -- path/to/your/file ...          # commit ONLY your paths (pathspec); -m BEFORE --
```

- **`git add <paths>` is NOT enough - use a pathspec commit.** `git commit` records the WHOLE index, so a
  sibling session's ALREADY-staged files get swept into your commit even when you only `git add`ed your
  own. Commit only your paths: `git commit -m "msg" -- <pathA> <pathB>` (the `-m` must come BEFORE `--`,
  or git reads it as a pathspec). Never `git add -A` / `-u`. Glance at `git status --short` first for any
  first-column `A`/`M` (already-staged) entries you did not create - those are the sweep risk, and the
  branch-guard below does NOT catch them (HEAD is not behind).
- **Exception: your change sits in a file that ALSO holds someone else's uncommitted edits.** A
  pathspec commit takes the WORKTREE copy of each named path, so it ships their edits under your
  message; `git add -p` fails too once the hunks cannot be separated (a table reformat re-padded
  every row). Build the blob yourself and commit WITHOUT a pathspec:

  ```bash
  cd "$(git rev-parse --show-toplevel)"           # FILE is the path from the repo root
  git show HEAD:FILE > /path/to/scratch/FILE      # HEAD's text: their edits are not in it
  # apply ONLY your change to the scratch copy (and reformat it, if the file needs that)
  H=$(git hash-object -w /path/to/scratch/FILE)
  M=$(git ls-files -s FILE | cut -d' ' -f1)       # keep the mode: 100755 for an executable
  git update-index --cacheinfo "$M,$H,FILE"
  git diff --cached --stat                        # the WHOLE index: only FILE may be listed
  git diff --cached FILE                          # only your change
  git commit -F msg                               # no pathspec
  ```

  Dropping the pathspec gives up the protection the rule above relies on, so check the whole index
  (`--stat` over every path), not only `FILE`: anything a sibling staged rides along otherwise.
  Never hard-code `100644`, which clears an executable's exec bit. Afterwards the worktree still
  holds their edits and `git status` still shows `FILE` modified, which is expected.
- A commit that succeeds but whose `git push` then says "Everything up-to-date" means you are NOT on the
  branch you think (detached, or a sibling's branch) - diagnose before re-pushing.
- **Durable fix: give each session its own `git worktree`** (`git worktree add ../wt-<name> <branch>`), so
  they never share a branch, index, or HEAD.
- **Enforced by this plugin:** the always-active `git-commit-branch-guard` hook runs these checks before a
  `git commit` and WARNS (never blocks), fail-open. It stays low-noise everywhere: the behind/diverged
  check runs in every repo (it fires only when origin moved under you - silent in normal feature-branch
  work, where you are ahead), while the louder "not on the default branch" check is OFF by default and
  enabled per-repo via `GIT_GUARD_STRICT_REPOS="repoA,repoB"` (basenames) - turn it on only for repos you
  work on a single branch directly, since "not on the default branch" is normal in a feature-branch flow.

## A push from a linked worktree exports GIT_DIR to your hooks

The per-session `git worktree` recommended above has one sharp edge. `git push` FROM a linked
worktree exports `GIT_DIR` into the environment of every hook it runs; a push from an ordinary
checkout does not, with or without `core.hooksPath`. Measured on git 2.53.0:

```
push from an ordinary checkout   GIT_DIR=unset
push from a linked worktree      GIT_DIR=<main>/.git/worktrees/<name>
```

So a hook that runs a TEST SUITE hands those tests the real repository. A fixture built the normal
way - `git init` a temp dir, then `git add`, then `git commit` - writes into the repo the hook is
guarding instead of into its own fixture, because the inherited `GIT_DIR` outranks the fixture's
cwd. Every git call still exits 0, so nothing reports it; you find out when origin has moved onto
a fixture commit.

**A hook must clear the repo-scoping variables before running anything that shells out to git:**

```bash
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES \
      GIT_COMMON_DIR GIT_NAMESPACE GIT_PREFIX GIT_QUARANTINE_PATH
```

In Python, DELETE those keys from a copy of `os.environ` for the child rather than passing a fresh
`env=` dict - a fresh dict replaces the whole environment and breaks the child in other ways.

**Clear them where the TESTS start too, not only in the hook.** A hook covers one launcher; any
other git-spawned runner hands over the same variables. In a repo whose tests shell out to git,
pop the list in a ROOT `conftest.py` (`pytest_configure`, before collection), so the suite is
hermetic whoever starts it, and prove it with a test that runs a fixture-building probe under a
sentinel repo as `GIT_DIR` and asserts the sentinel's config is untouched.

**After a suspected leak, look past the refs.** A fixture's `git config user.name` / `user.email`
lands in the SHARED config and then authors every later commit, and it looks like a configured
value. Diff the shared config against a clean clone's
(`git config --file <common-dir>/config --list`: `user.*`, `core.bare`, `core.hooksPath`,
remotes) and check `git log --format='%an <%ae>'` for an author nobody configured. Repair: remove
the leaked `user.name`/`user.email` (and any other entry the fixture wrote, never one you set
yourself, such as a deliberate `core.hooksPath`) from the shared config, set `core.bare` back to
`false`, restore `refs/remotes/origin/*` from the remote (read the real tip from the remote, never
the local ref), and re-point the hijacked branch at its real tip, which is
still in the object store. When a suite fails only under a hook, or a repo grows commits nobody
wrote, check this before debugging the tests.

## Tools

`git_state.py` automates the pre-commit / pre-push state check above across one or many repos
(read-only): for each repo it prints the branch, whether HEAD is in sync with its upstream
(ahead/behind/diverged, `no-upstream`, or an upstream gone on the remote), the dirty count and
each staged file; it exits 1 if ANY repo is out of sync and 2 if the check was incomplete (a repo
git could not read, or a `--root` that is missing, holds no repo, or has an unreadable directory) -
so it doubles as a bulk pre-push guard. Add `--json` for the `{ok, command, data, skipped}`
envelope: `ok` is true on BOTH exit 0 and exit 1 (it ran and answered, even "out of sync"),
false only on exit 2 (it could not run).

It ships ONCE, in the skill that owns the jigs: `skills/compuse-toolbox/scripts/git_state.py`
(see `bitranox:compuse-toolbox` for the rest of them).

```bash
uv run <plugin>/skills/compuse-toolbox/scripts/git_state.py                 # current directory
uv run <plugin>/skills/compuse-toolbox/scripts/git_state.py repoA repoB     # named repos
uv run <plugin>/skills/compuse-toolbox/scripts/git_state.py --root ~/src    # every repo below a dir (a .git dir, or a worktree's or submodule's .git file)
```

## Hooks

`repo-gate` (PreToolUse on Bash and PowerShell, and `--ci`) blocks a commit on a failing gate (tests-exist, pytest, JSON valid, LF endings, the meta-using-bitranox-skills index in sync, and no leaked secrets/private data). `git-footgun-guard` blocks the always-broken `git rev-parse --short <2+ revs>` before it produces the confusing error. `git-commit-branch-guard` warns (never blocks) before a `git commit` when local HEAD is behind/diverged from its upstream (origin moved under you), and - for repos in `GIT_GUARD_STRICT_REPOS` - when you are off the default branch or detached.
