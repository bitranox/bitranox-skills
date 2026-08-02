---
name: meta-audit-local-skills-and-hooks
description: Use when reviewing the Claude Code skills and hooks on a machine that no plugin ships - a personal ~/.claude/skills or ~/.claude/hooks entry, a project's .claude/skills, a hook registered in settings.json - or when a local hook silently stopped firing, a tests dir exists but nothing actually runs, a retired shim sits beside its replacement, or a local skill duplicates a marketplace one
---

# Auditing local skills and hooks

## Overview

A marketplace skill is gated from several directions: a commit gate, a clean-room catalogue audit,
mirror checks, a tests-per-script rule. None of that reaches a file outside the marketplace repo.
Everything else a machine loads - a personal skill, a project's `.claude/skills`, a hook wired in
`settings.json` - runs with no gate at all, and rots quietly.

**The core principle: audit by OWNERSHIP, never by path.** The same shipped skill is reachable at
three paths at once (the source checkout, the marketplace clone, the version cache), and tool repos
ship mirrored twins on top of that. Selecting by "where does it look like a skill" reviews all of
them and, far worse, invites an edit into content some other gate owns.

## Step 1 - ask what you are allowed to touch, and read the answer

Never start from a `find`. Run this first, every time:

```bash
bash <plugin>/hooks/run-python.sh \
  <plugin>/skills/meta-audit-local-skills-and-hooks/scripts/audit_local.py \
  targets --root <tree>
```

(home: `skills/meta-audit-local-skills-and-hooks/`, launched through `hooks/run-python.sh`.)

It prints what it selected AND what it skipped with the reason. Read both halves. The skipped list
is the proof the ownership filter ran, not noise to scroll past.

| Location                                                                             | Verdict                                                   |
|--------------------------------------------------------------------------------------|-----------------------------------------------------------|
| `~/.claude/skills`, `~/.claude/hooks`                                                | yours - audit and fix                                     |
| a project's `.claude/skills`                                                         | yours - audit and fix                                     |
| any dir under an ancestor holding `.claude-plugin/plugin.json` or `marketplace.json` | owned by that plugin - REPORT ONLY                        |
| anything under `~/.claude/plugins/`                                                  | an installed copy - REPORT ONLY, an edit there evaporates |

**You may not edit a file the selection skipped.** Not to keep copies consistent, not because it
is "the same skill", not because the fix is one line. A skipped file belongs to a repo with its own
version bump, review artifact and mirror ritual; editing it bypasses all three and is how a twin
silently drifts. Report it and stop.

## Step 2 - run the deterministic checks

```bash
... audit_local.py check --root <tree> --shipped <marketplace>/skills
```

Anything a script can decide, a script decides: registrations that name a missing file, hook
scripts nothing registers, malformed tombstones, test dirs that cannot collect, skills shipping a
script with no test, front matter whose name disagrees with its directory or whose description is
not trigger-first, a local skill duplicating a shipped one, a local hook or skill script the
marketplace now ships too (`duplicate-of-shipped`), and graveyards.

Pass `--shipped <marketplace>/skills` or the duplicate checks stay silent - the run has nothing to
compare against and cannot tell you so.

Three of those repay a closer look, because the obvious version of each check is wrong:

- **A `tests/` dir that exists is not a `tests/` dir that runs.** The check collects it. A module
  importing a retired shim dies at import, so every "does it have tests?" check reports it green.
- **A retired shim is not rot - it is the fix.** A tombstone that exits non-zero is what makes a
  stale caller fail loudly instead of silently skipping a guard. Deleting one re-arms the trap.
  The check asks whether it is well formed (non-executable, exits non-zero, names a replacement,
  registered nowhere), never whether it should exist. Read the mode; do not assert it.
- **A duplicate is not automatically the local copy's fault.** `duplicate-of-shipped` reports the
  pair, never a verdict, because the local side can be AHEAD - a fix applied here, or a wider scope
  than the shipped one covers. So the finding splits: byte-IDENTICAL means retiring the local copy
  costs nothing and is the fix; DIFFERS means read the diff and say which side holds what before
  touching anything. If the local copy is ahead, CONTRIBUTE that upstream and retire it only once
  the improvement lands - deleting it to "dedup" throws the improvement away, which is a worse
  outcome than the duplicate. Whatever still invokes the local path gets repointed either way.

## Step 3 - review the prose

Only then spend reviewers, one per skill, staging just the skills dir so a huge parent is never
copied into the room:

```bash
bash <plugin>/hooks/run-python.sh <plugin>/skills/meta-skill-audit/scripts/audit_skills.py \
  --skills-dir <target> --room <dir outside the tree>
```

**REQUIRED BACKGROUND:** `bitranox:meta-skill-audit` owns the reviewer half - the finding classes,
the clean-room contamination defence, and the rule that a clean report means unmeasured, not
verified. Do not restate it here.

## Fixing

Fix what a check reported. Do not widen the rule and sweep for what you infer it implies.

| Finding                                                             | Authority                                          |
|---------------------------------------------------------------------|----------------------------------------------------|
| provably dead (uncollectable test, orphan bytecode, stale node ids) | apply in any mode                                  |
| content edit to a local `SKILL.md`                                  | follow the dream mode: propose, or apply in `auto` |
| anything the selection skipped                                      | report only, never edit                            |

A project's skills follow that project's mode, not the machine's.

## Rationalizations

| Thought                                                            | Reality                                                                                |
|--------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| "I'll fix every copy so they stay consistent"                      | The copies are one skill with one owner. Consistency is that owner's release job.      |
| "The cache is just a copy, editing it is harmless"                 | The next marketplace update overwrites it. The fix is gone and you believe it shipped. |
| "It is the same one-line rule, so the same fix applies everywhere" | A tool repo's twin needs a version bump and a mirror check. A raw edit is drift.       |
| "The rule obviously also covers this vaguer case"                  | Then the check should say so. Widening it by hand edits files nobody reviewed.         |
| "This retired shim is dead code, delete it"                        | It is a live tombstone. Deleting it makes a stale caller silently skip a guard.        |
| "The `tests/` dir is there, so it is covered"                      | Existing is not running. Collect it.                                                   |
| "`find` already showed me every skills dir"                        | It also showed you three copies of one shipped skill.                                  |

## Red flags - stop

- About to edit a path the `targets` run listed under "skipped"
- About to delete a file whose header says RETIRED
- Reporting a file's permissions, owner or content without having read them
- Fixing a class of problem no check reported
- Treating two paths as two skills without checking whether one repo owns both

## Common mistakes

- **Starting from a tree walk.** Discovery finds `.claude/skills` dirs; ownership decides which are
  yours. Skipping step 1 is how a tool repo gets edited.
- **Auditing a worktree twice.** A linked worktree is a second checkout of one repo; the selection
  de-duplicates by repository identity, a hand-rolled list does not.
- **Reporting a clean run as verified.** One reviewer per skill is a sample.

## When the dreams run this

`bitranox:meta-dream-crosstree-deep` runs the personal half, because `~/.claude` is machine-global.
`bitranox:meta-dream-tree` runs the project half for its own tree, with `--no-personal`, because a
project's skills belong to that tree and get checked far more often there.
