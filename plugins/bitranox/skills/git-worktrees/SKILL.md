---
name: git-worktrees
description: Use when starting feature work that needs an isolated workspace or worktree separate from the current branch, or before executing an implementation plan that should not disturb the current checkout, or when finishing with a worktree - deleting one leaves its per-topic build cache behind outside the checkout, so the disk stays full and nothing lists what to reclaim - or before discarding a leftover worktree's uncommitted files or deleting a branch whose work may already be on master, merged squashed, cherry-picked or copied in by hand, where git cherry says it is not
---

# Git Worktrees

> Adapted from the superpowers plugin (MIT).

## Overview

Ensure work happens in an isolated workspace. Prefer your platform's native worktree tools. Fall back to manual git worktrees only when no native tool is available.

**Core principle:** Detect existing isolation first. Then use native tools. Then fall back to git. Never fight the harness.

**Announce at start:** "I'm using the git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

**Before creating anything, check if you are already in an isolated workspace.**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

**Submodule note:** a plain submodule does NOT trip this test - measured with these exact commands,
`GIT_DIR` and `GIT_COMMON` both resolve to `<super>/.git/modules/<name>`, so they compare equal and
the submodule reads as a normal checkout, which is how you want to treat it. The pair differs only
in a linked worktree. Run this if you want it stated explicitly, or when a submodule may itself
have a worktree attached:

```bash
# Returns a path when you are inside a submodule; empty otherwise
git rev-parse --show-superproject-working-tree 2>/dev/null
```

**If `GIT_DIR != GIT_COMMON` (and not a submodule):** You are already in a linked worktree. Skip to Step 2 (Project Setup). Do NOT create another worktree.

Report with branch state:
- On a branch: "Already in isolated workspace at `<path>` on branch `<name>`."
- Detached HEAD: "Already in isolated workspace at `<path>` (detached HEAD, externally managed). Branch creation needed at finish time."

**If `GIT_DIR == GIT_COMMON` (or in a submodule):** You are in a normal repo checkout.

Has the user already indicated their worktree preference in your instructions? If not, ask for consent before creating a worktree:

> "Would you like me to set up an isolated worktree? It protects your current branch from changes."

Honor any existing declared preference without asking. If the user declines consent, work in place and skip to Step 2.

## Step 1: Create Isolated Workspace

**You have two mechanisms. Try them in this order.**

### 1a. Native Worktree Tools (preferred)

The user has asked for an isolated workspace (Step 0 consent). Do you already have a way to create a worktree? It might be a tool with a name like `EnterWorktree`, `WorktreeCreate`, a `/worktree` command, or a `--worktree` flag. If you do, use it and skip to Step 2 (but read the base-branch exception below first when the work needs unpushed commits).

Native tools handle directory placement, branch creation, and cleanup automatically. Using `git worktree add` when you have a native tool creates phantom state your harness can't see or manage.

**Native tools branch from origin's default branch, not from local HEAD.** `EnterWorktree` with
`name`, and a subagent dispatched with `isolation: "worktree"`, both take their base from the
`worktree.baseRef` setting, and its default `fresh` means origin/<default-branch> (local HEAD
only when there is no remote or `origin/HEAD` cannot be resolved). Commits that exist only
locally (not pushed yet, say behind a slow push gate) are missing from that base, and nothing
says so. Before either one, when the work builds on unpushed commits:

- Prefer setting `baseRef` to `"head"`. It is a NESTED key, `{"worktree": {"baseRef": "head"}}`;
  a flat `"worktree.baseRef"` key sets nothing and worktrees keep branching from origin. Put it in
  the repository's `.claude/settings.local.json` rather than the user settings, so it does not
  switch every repository on the machine. It applies to `--worktree`, `EnterWorktree` and agent
  isolation alike, and new worktrees then branch from your current local HEAD.
- Or create the worktree from HEAD yourself,
  `git worktree add .claude/worktrees/<name> -b <name> HEAD` (check `.claude/worktrees` is
  gitignored first), and enter it with `EnterWorktree` and `path`. Keep it under
  `.claude/worktrees/` of the same repository: that is where `path` expects a worktree, and
  outside it the switch asks for permission or is refused (observed in Claude Code 2.1.310). For
  a subagent, pass that directory as an ABSOLUTE path in the Agent `cwd` where the tool offers
  that parameter (not every build does; `cwd` and `isolation: "worktree"` are mutually
  exclusive); where it does not, set `baseRef` as above or brief the subagent with absolute paths
  into the worktree. This is the one case where `git worktree add` beside a native tool is right.
- Either way, confirm the expected local commit is in the new worktree: inside it,
  `git merge-base --is-ancestor <sha> HEAD` exits 0.

**Bringing an isolated subagent's work back:** its commits were written and tested on its base,
not on yours, so its green says nothing about the combination. Cherry-pick its commits onto your
branch and re-run the full suite there before treating the work as landed. For several branches
at once (pick the tip, union additive conflicts, keep red commits off main) see
bitranox:process-agents-dispatching-parallel, "Review and Integrate".

Only proceed to Step 1b if you have no native worktree tool available.

### 1b. Git Worktree Fallback

**Only use this if Step 1a does not apply** - you have no native worktree tool available. Create a worktree manually using git.

#### Directory Selection

Follow this priority order. Explicit user preference always beats observed filesystem state.

1. **Check your instructions for a declared worktree directory preference.** If the user has already specified one, use it without asking.

2. **Check for an existing project-local worktree directory:**
   ```bash
   ls -d .worktrees 2>/dev/null     # Preferred (hidden)
   ls -d worktrees 2>/dev/null      # Alternative
   ```
   If found, use it. If both exist, `.worktrees` wins.

3. **If there is no other guidance available**, default to `.worktrees/` at the project root.

4. **Bind the outcome**, because every step below refers to the directory you just chose:
   ```bash
   LOCATION=$(ls -d .worktrees 2>/dev/null || ls -d worktrees 2>/dev/null || echo .worktrees)
   BRANCH_NAME=<your-topic-branch>
   ```

#### Safety Verification (project-local directories only)

**MUST verify directory is ignored before creating worktree:**

```bash
# Check the directory you CHOSE, not both names. `git check-ignore` matches a PATHNAME and
# does not care whether it exists, so testing both with `||` reports "ignored" whenever
# EITHER name is listed - including the one you are not about to use.
git check-ignore -q "$LOCATION" 2>/dev/null
```

**If NOT ignored:** Add to .gitignore, commit the change, then proceed.

**Why critical:** Prevents accidentally committing worktree contents to repository.

#### Create the Worktree

```bash
# $LOCATION and $BRANCH_NAME were bound in Directory Selection above. Unset, this
# expands to "/<branch>" at the filesystem root, and the failure looks like a sandbox denial.
path="$LOCATION/$BRANCH_NAME"

git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

**Sandbox fallback:** If `git worktree add` fails with a permission error (sandbox denial), tell the user the sandbox blocked worktree creation and you're working in the current directory instead. Then run setup and baseline tests in place.

## Step 2: Project Setup

Auto-detect and run appropriate setup:

```bash
# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Python (prefer uv)
if [ -f pyproject.toml ]; then uv sync 2>/dev/null || uv pip install -e .; fi
if [ -f requirements.txt ]; then uv pip install -r requirements.txt 2>/dev/null || pip install -r requirements.txt; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

## Step 3: Verify Clean Baseline

Run tests to ensure workspace starts clean:

```bash
# Use project-appropriate command
npm test / cargo test / pytest / go test ./...
```

**If tests fail:** Report failures, ask whether to proceed or investigate.

**If tests pass:** Report ready.

**A worktree nested in the main checkout inherits the tool config ABOVE it.** A project-local
worktree (`.worktrees/<name>`, `.claude/worktrees/<name>`) sits inside the main checkout, so a
tool that searches upward for its config can find the main checkout's file before, or instead
of, the worktree's own. Measured with pyright 1.1.407: run from a worktree under
`.claude/worktrees/<name>`, it loaded the main checkout's `pyrightconfig.json` and ignored the
worktree's own `[tool.pyright]` in `pyproject.toml` - 0 errors where the worktree's strict setting
reports 4. A green type check there can be the parent's laxer config talking. Before trusting a
type-check or lint result in such a worktree, check which config the tool loaded:

```bash
pyright --verbose 2>&1 | grep "Loading configuration"   # must name a file INSIDE the worktree
pyright -p .                                           # pin the worktree's own config
```

A worktree outside the checkout (the `<base>/wt-<topic>` convention) has nothing above it to
inherit, which is one reason to prefer it when the project's tools read upward-found config.

### Report

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Step 4: Finishing - First Check the Work Landed (landed)

Ask this BEFORE `--discard-uncommitted` or `git branch -D`, never after. `git cherry` and
`git merge-base --is-ancestor` answer it badly: work that landed SQUASHED, rebased, or copied
into a master commit by hand reads as unlanded, and a worktree's uncommitted files are not
commits at all. `scripts/landed.py` (in this skill's directory) answers it from content, and
only reads - it never writes the index or any ref:

```
uv run scripts/landed.py .claude/worktrees/my-feature      # a worktree: its files AND its commits
uv run scripts/landed.py my-feature --into main             # a branch on its own
uv run scripts/landed.py my-feature --json                  # {ok, command, data, skipped}
```

- **A worktree's changed, deleted and untracked files** are hashed as git would store them and
  compared with the target's copy, then with every target commit since the merge-base that
  touched the path - so a file master changed AGAIN after the work landed still counts.
- **A branch's commits** count as landed when each one is patch-equivalent (what `git cherry`
  checks) OR every line the branch added is present in the target's copy of its file, matched
  as a multiset. The second test is what catches a squash. It is evidence, not proof: a line
  counts wherever in the file it sits, so read the diff yourself when the stakes are high.
- A worktree is landed only when its files AND its commits both are.
- **Gitignored files are not checked** (a `.venv`, build output): they are taken as
  regenerable. Removing the worktree deletes them even WITHOUT `--discard-uncommitted` - git
  refuses over an untracked file, never over an ignored one - so copy out any you need first.
- `--into` defaults to the first of `origin/HEAD`, `origin/main`, `origin/master`, `main`,
  `master` that resolves - fetch first, since a stale `origin/*` gives a confident stale answer.
- Exit 0 = landed, 1 = not landed, 2 = could not run. The text output names each unlanded file
  with its status and up to five missing lines per file; `--json` carries all of them.

Only a 0 makes `--discard-uncommitted` safe; a 2 is not a 0. On a 1, save what it names first -
commit it on the branch or copy it out of the checkout - and re-run until it exits 0.

## Step 5: Finishing - Reclaim the Per-Topic Build Cache (wtclean)

`git worktree remove` deletes the checkout and nothing else. The per-worktree build cache from
Step 2 lives OUTSIDE the checkout on purpose (that is what stops several worktrees fighting over
one `CARGO_TARGET_DIR`), so it survives the removal and piles up invisibly - usually noticed only
when the disk fills.

**First check nothing still runs from the worktree.** A process launched from it - a background
CI waiter, a gate, a dev server - keeps the deleted directory as its working directory, and its
next git call fails, exit 128:
`fatal: Unable to read current working directory: No such file or directory` (in the C locale;
Python's `os.getcwd()` raises `FileNotFoundError`). A CI waiter that runs git, or resolves the
repository, on every poll then exits non-zero on a run that was green, and the failure reads as
red CI. (compuse-toolbox's `ci_wait.py` resolves the repository once at start and survives the
removal; only when that first lookup failed does it warn on stderr that removing the directory
will break its polls.) Neither `git worktree remove` nor `wtclean.py` checks
for this: on Linux and macOS the removal succeeds under the running process (Windows locks a
process's current directory, so there it fails instead). A merged branch does not make it safe.
Wait for your own background job to finish and read its recorded exit code, then, from OUTSIDE
the worktree (run inside it, the check lists your own shell and session), check that no other
process has its cwd there:

```bash
cd /path/to/main-checkout                       # not the worktree
ls -l /proc/[0-9]*/cwd 2>/dev/null | grep -E ' -> /path/to/worktree(/|$)'   # Linux; none = clear
lsof +D /path/to/worktree                                                   # macOS, or with lsof
```

The anchored pattern keeps a sibling such as `/path/to/worktree-2` from matching.

`scripts/wtclean.py` removes the worktree AND those caches together, and shows what it will take
before it takes anything:

```
uv run scripts/wtclean.py my-feature                 # the plan, with sizes - deletes nothing
uv run scripts/wtclean.py my-feature --apply         # remove exactly what the plan listed
uv run scripts/wtclean.py .worktrees/my-feature --cache-dir ~/.cache/targets/my-feature --apply
```

**Cache locations are a convention, not a discovery.** Git cannot be asked where your build cache
lives, so the default candidates are `<base>/wt-<topic>-target` and `<base>/wt-<topic>-clippy`,
with `<base>` your home directory. If yours live somewhere else, name them with `--cache-dir`
(repeatable) or adjust `--base` / `--prefix` / `--cache-suffix`. A run that matches nothing says
which paths it checked rather than reporting an empty plan as though you had no caches.

**The worktree is found the same way, and the search is wider than the cache one.** A bare
topic resolves to the first of these that exists: `<base>/wt-<topic>`, then `.worktrees/<topic>`,
`worktrees/<topic>` and `.claude/worktrees/<topic>` under the directory you run it from, which
covers both layouts Step 1b creates and the one the native worktree tool creates. Naming
`--base` confines the search to that base. Any other layout is reached by passing the worktree
path outright (`wtclean.py .config/wt/my-feature`) instead of the bare name.

Two consequences worth knowing before you trust a bare name:

- **The three project-local candidates are relative to the directory you run from**, not to the
  repository root, so running it from a subdirectory checks paths that do not exist and leaves
  `<base>` as the only real candidate. Run it from the directory that holds `.worktrees/` or
  `.claude/worktrees/`.
- **A bare topic matching more than one candidate is REFUSED**, naming each one, and no flag
  overrides it - `--discard-uncommitted` answers "delete it anyway", not "pick one for me".
  The refusal covers the CACHES too, unlike every other worktree refusal: cache candidates are
  built from the topic alone, so two checkouts sharing a name share them, and a run that could
  not resolve the name must not delete anything derived from it. A dirty or symlinked worktree
  is a RESOLVED one, so its caches are unambiguously its own and still go.
  A stale `<base>/wt-<topic>` beside a real project-local checkout is a question, and this is
  a delete with no undo, so answer it by passing the path you mean. When exactly one matches,
  the plan names it on its `would remove` line.

A search that finds nothing names every path it tried, which is the half that was missing when a
bare name reaching only `<base>` reported `nothing to remove` for a 513 MB checkout sitting in
`.claude/worktrees/`.

What it refuses, because a delete is not undoable. Every refusal below is decided at PLAN time,
so the dry run lists them as `REFUSED` rather than leaving them for `--apply` to discover. An
`--apply` can still report a `FAILED` on top of those - a removal that git or the filesystem
rejects is not knowable until it is attempted:

- **It is a dry run until `--apply`**, and `--apply` removes exactly what the plan listed - it
  does not re-scan, so a directory created after you read the plan is not swept up with it.
- **A worktree holding uncommitted or untracked work** is refused. `--discard-uncommitted`
  overrides that and forwards `--force` to `git worktree remove`, which DISCARDS the work.
- **A target that is a symbolic link** is refused: removing through a link can destroy data
  outside the directory you named. On Windows this does not cover a directory JUNCTION, which is
  not reported as a symbolic link; the "resolves outside the base" refusal is what covers that.
- **A parent reference anywhere in the argument** (`../../etc`, `wt-a/../../etc`) is refused
  outright, never normalised - taking the basename first would turn `../../etc` into the
  innocent-looking name `etc`. A path WITHOUT a parent reference is not refused: it names the
  worktree directly (relative to where you run from, like any path you type), which is what
  the third example above does. What has to be a bare name is the TOPIC, and the topic is the
  argument's last path segment - it is what the cache candidates are built from. The prefix is
  stripped only from a worktree on the `<base>/wt-<topic>` convention: inside `.worktrees/`,
  `worktrees/` or `.claude/worktrees/` the name is kept whole, so `.worktrees/wt-cache` looks for
  `<base>/wt-wt-cache-target` and never touches `<base>/wt-cache-target`, which belongs to a
  different worktree.
- **A `--cache-dir` that does not exist** is refused by name with exit 2, dry run included (a typo
  would otherwise read as "nothing to remove" and exit 0 while the real cache stays on disk).
- **A path that is your home directory or a filesystem root** is refused, `--cache-dir` included;
  a `--cache-dir` refused that way (or as a symlink) exits 2, since the path you typed is the
  problem.

Works for a worktree of an ordinary checkout, a bare repository and a `--separate-git-dir` one:
git is run from the repository's common git dir. The removal has no timeout, because killing git
part way through would leave a half-deleted, still-registered worktree. A size that could not be
read in full is shown as `at least`.

Exit codes: 0 = nothing blocked; 1 = the plan refused something (a dirty or unreadable worktree,
an ambiguous topic) and nothing failed; 2 = could not run as asked - a usage error, an unsafe
topic, a missing or forbidden `--cache-dir`, or a removal that FAILED (git refused, an I/O error).
A 2 wins over a 1. `--json` emits `{ok, command, data, skipped}` on every exit, `ok` false only on
exit 2, each blocked entry's `kind` (`refused`, `bad_input`, `failed`) under `data.blocked`;
warnings go to stderr.

## Quick Reference

| Situation                                                          | Action                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Already in linked worktree                                         | Skip creation (Step 0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| In a submodule                                                     | Treat as normal repo (Step 0 guard)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Native worktree tool available                                     | Use it (Step 1a)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| No native tool                                                     | Git worktree fallback (Step 1b)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `.worktrees/` exists                                               | Use it (verify ignored)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `worktrees/` exists                                                | Use it (verify ignored)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Both exist                                                         | Use `.worktrees/`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Neither exists                                                     | Check instruction file, then default `.worktrees/`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Directory not ignored                                              | Add to .gitignore + commit                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Permission error on create                                         | Sandbox fallback, work in place                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Tests fail during baseline                                         | Report failures + ask                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| No package.json/Cargo.toml                                         | Skip dependency install                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Returning to an OLD worktree                                       | `git status --porcelain` FIRST - a long-lived worktree can hold an abandoned prior op's dirty state; `git stash push -u` it. Never `commit -a` over it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Sharing a build cache dir                                          | Give each worktree its OWN `CARGO_TARGET_DIR` (or equivalent). One shared incremental cache across trees with different sources serializes builds on the target lock, and makes the compiler link the OTHER worktree's crate and emit phantom errors that name real symbols - so it reads as a defect in the code in front of you and sends you editing correct code. THE TELL: grep your own worktree for the name the compiler SUGGESTS; zero hits means you are reading a sibling's build. (Measured: nine errors of the form `no method named X found, help: there is a method X_ns with a similar name`, where the suggested name existed in no file of the tree being built.) Use a compiler cache (sccache) for cross-tree reuse instead. |
| Worktree deleted, disk still full                                  | Its per-topic build cache is still there - `git worktree remove` never touches it. `uv run scripts/wtclean.py <topic> [--apply]` (Step 5)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| About to discard a dirty worktree or `branch -D` a squashed branch | `uv run scripts/landed.py <worktree-or-branch>` FIRST; only exit 0 (landed) makes the discard safe (Step 4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Common Mistakes

### Fighting the harness

- **Problem:** Using `git worktree add` when the platform already provides isolation
- **Fix:** Step 0 detects existing isolation. Step 1a defers to native tools.

### Skipping detection

- **Problem:** Creating a nested worktree inside an existing one
- **Fix:** Always run Step 0 before creating anything

### Skipping ignore verification

- **Problem:** Worktree contents get tracked, pollute git status
- **Fix:** Always use `git check-ignore` before creating project-local worktree

### Assuming directory location

- **Problem:** Creates inconsistency, violates project conventions
- **Fix:** Follow priority: explicit instructions > existing project-local directory > default

### Trusting a check that read the parent's config

- **Problem:** In a worktree nested in the main checkout, pyright (and any tool that searches
  upward for its config) can load the main checkout's config instead of the worktree's own, so a
  green result reflects the wrong settings
- **Fix:** Check the loaded config path (`pyright --verbose`), pin it (`pyright -p .`), or create
  the worktree outside the checkout (Step 3)

### Proceeding with failing tests

- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

## Red Flags

**Never:**
- Create a worktree when Step 0 detects existing isolation
- Use `git worktree add` when you have a native worktree tool (e.g., `EnterWorktree`). This is the #1 mistake - if you have it, use it. The one exception: the work needs unpushed local commits and `worktree.baseRef` is not `head` (Step 1a).
- Remove a worktree while a process launched from it is still running (Step 5)
- Skip Step 1a by jumping straight to Step 1b's git commands
- Create worktree without verifying it's ignored (project-local)
- Skip baseline test verification
- Proceed with failing tests without asking

**Always:**
- Run Step 0 detection first
- Prefer native tools over git fallback
- Follow directory priority: explicit instructions > existing project-local directory > default
- Verify directory is ignored for project-local
- Auto-detect and run project setup
- Verify clean test baseline
