---
name: git-worktrees
description: Use when starting feature work that needs an isolated workspace or worktree separate from the current branch, or before executing an implementation plan that should not disturb the current checkout, or when finishing with a worktree - deleting one leaves its per-topic build cache behind outside the checkout, so the disk stays full and nothing lists what to reclaim
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

The user has asked for an isolated workspace (Step 0 consent). Do you already have a way to create a worktree? It might be a tool with a name like `EnterWorktree`, `WorktreeCreate`, a `/worktree` command, or a `--worktree` flag. If you do, use it and skip to Step 2.

Native tools handle directory placement, branch creation, and cleanup automatically. Using `git worktree add` when you have a native tool creates phantom state your harness can't see or manage.

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

#### Safety Verification (project-local directories only)

**MUST verify directory is ignored before creating worktree:**

```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**If NOT ignored:** Add to .gitignore, commit the change, then proceed.

**Why critical:** Prevents accidentally committing worktree contents to repository.

#### Create the Worktree

```bash
# Determine path based on chosen location
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

### Report

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Step 4: Finishing - Reclaim the Per-Topic Build Cache (wtclean)

`git worktree remove` deletes the checkout and nothing else. The per-worktree build cache from
Step 2 lives OUTSIDE the checkout on purpose (that is what stops several worktrees fighting over
one `CARGO_TARGET_DIR`), so it survives the removal and piles up invisibly - usually noticed only
when the disk fills.

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

What it refuses, because a delete is not undoable:

- **It is a dry run until `--apply`**, and `--apply` removes exactly what the plan listed - it
  does not re-scan, so a directory created after you read the plan is not swept up with it.
- **A worktree holding uncommitted or untracked work** is refused. `--discard-uncommitted`
  overrides that and forwards `--force` to `git worktree remove`, which DISCARDS the work.
- **A target that is a symbolic link** is refused: removing through a link can destroy data
  outside the directory you named. On Windows this does not cover a directory JUNCTION, which is
  not reported as a symbolic link; the "resolves outside the base" refusal is what covers that.
- **A topic that is a path rather than a bare name** is refused outright, never normalised - the
  basename of `../../etc` is the innocent-looking name `etc`.

Exit codes: 0 = nothing blocked, 1 = something was refused or could not be removed, 2 = usage
error. `--json` emits the machine-readable envelope; warnings go to stderr.

## Quick Reference

| Situation                         | Action                                                                                                                                                                                                                                                                                      |
|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Already in linked worktree        | Skip creation (Step 0)                                                                                                                                                                                                                                                                      |
| In a submodule                    | Treat as normal repo (Step 0 guard)                                                                                                                                                                                                                                                         |
| Native worktree tool available    | Use it (Step 1a)                                                                                                                                                                                                                                                                            |
| No native tool                    | Git worktree fallback (Step 1b)                                                                                                                                                                                                                                                             |
| `.worktrees/` exists              | Use it (verify ignored)                                                                                                                                                                                                                                                                     |
| `worktrees/` exists               | Use it (verify ignored)                                                                                                                                                                                                                                                                     |
| Both exist                        | Use `.worktrees/`                                                                                                                                                                                                                                                                           |
| Neither exists                    | Check instruction file, then default `.worktrees/`                                                                                                                                                                                                                                          |
| Directory not ignored             | Add to .gitignore + commit                                                                                                                                                                                                                                                                  |
| Permission error on create        | Sandbox fallback, work in place                                                                                                                                                                                                                                                             |
| Tests fail during baseline        | Report failures + ask                                                                                                                                                                                                                                                                       |
| No package.json/Cargo.toml        | Skip dependency install                                                                                                                                                                                                                                                                     |
| Returning to an OLD worktree      | `git status --porcelain` FIRST - a long-lived worktree can hold an abandoned prior op's dirty state; `git stash push -u` it. Never `commit -a` over it.                                                                                                                                     |
| Sharing a build cache dir         | Give each worktree its OWN `CARGO_TARGET_DIR` (or equivalent). One shared incremental cache across trees with different sources serializes builds on the target lock and can emit phantom errors that only a full clean fixes. Use a compiler cache (sccache) for cross-tree reuse instead. |
| Worktree deleted, disk still full | Its per-topic build cache is still there - `git worktree remove` never touches it. `uv run scripts/wtclean.py <topic> [--apply]` (Step 4)                                                                                                                                                   |

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

### Proceeding with failing tests

- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

## Red Flags

**Never:**
- Create a worktree when Step 0 detects existing isolation
- Use `git worktree add` when you have a native worktree tool (e.g., `EnterWorktree`). This is the #1 mistake - if you have it, use it.
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
