---
name: meta-consolidate-claude-md
description: Use when the same guidance is copy-pasted across many CLAUDE.md (or other always-loaded doc) files in a tree and has drifted - a section repeated in 20 repos, a rule stated at three levels, a table that no longer matches the tool it documents. Covers measuring the duplication, verifying each claim against ground truth before keeping it, converging the variants to one correct text, and lifting it to the true common ancestor without leaving a reader meeting the same heading twice.
---

# Consolidating duplicated CLAUDE.md content

Copy-pasted guidance does not stay identical. It forks, and each fork ages separately, so the
duplication problem becomes a CORRECTNESS problem: some copies now describe a tool that changed, a
file that was deleted, a target that never existed. Deduplicating without checking which copy is
right just picks one lie and installs it at an ancestor, where it binds every repo below.

**The order is: measure, verify, converge, lift.** Skipping straight to the lift is the failure this
skill exists to prevent.

## 1. Measure - byte-identical groups and their true common ancestor

`scripts/claudemd_variance.py` does this measurement, so it never needs hand-rolling again - two
sessions wrote this exact script from scratch before it shipped:

```
uv run scripts/claudemd_variance.py --root ~/src --json
```

It splits every `CLAUDE.md` into `## ` sections, hashes each body (whitespace-normalised, so
trivial reflowing does not read as a different variant - the definition is in `--help`), groups
the identical ones, and reports each group's common ancestor plus the largest variant's share of
the group. For each group of 3+, its common ancestor - not the one you assumed - is where the
text belongs; `--lift-threshold` marks which variants clear that bar.

Enumeration is a plain filesystem WALK, never the session `grep` or any gitignore-aware tool:
`grep` routes to a gitignore-aware backend and silently drops ignored files. Measured on one
tree: 73 files by walk, 17 by grep, no warning. `claudemd_variance.py` never shells out at all,
so it structurally cannot inherit that blind spot; `bitranox:compuse-toolbox`'s `grep_all` is the
right tool when the question is a text search rather than this section-level measurement.

Then split the variance by CAUSE, because only one kind is liftable:

| Variance                                                         | Verdict                                                                                                                                                                                                         |
|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Section embeds the package/repo name                             | NOT liftable - the name is the point. Leave it per-repo.                                                                                                                                                        |
| Copies differ only in whitespace                                 | Converge, then lift.                                                                                                                                                                                            |
| Copies differ in substance (drift)                               | Verify each against ground truth first, THEN converge. Section 2.                                                                                                                                               |
| Copies share only a closing pointer sentence; the body is unique | LEAVE IT - the shared bytes are one trailing sentence, not the section. A "largest variant covers X%" reading can be that sentence's share of a short body, not real duplication. Read the body before lifting. |
| Every copy is unique (N copies, N variants)                      | Nothing shared to extract. Leave it.                                                                                                                                                                            |

A useful signal for whether a lift will be clean: how much of the copies the largest variant covers.
Around 60-75% means one dominant version to lift. Around 30% means the section has forked and
lifting any one variant leaves most repos double-loaded.

## 2. Verify - a correctness review, not a popularity contest

**Different does not mean one of them is right.** The most-copied variant is usually the oldest.
Judge each claim against the system, not against the other copies:

- A named FILE or DIRECTORY: does it exist? Check in several carriers, not one.
- A named COMMAND or TARGET: does the tool actually provide it? For a generated `Makefile`, the
  generator owns the list, so the doc is a snapshot that will drift by design.
- A named SKILL, flag, or config key: does it resolve today?
- A MECHANISM ("this dir is template-managed", "payloads are sanitized"): find the code that does
  it. If there is none, the line is aspiration, not documentation.

A claim you cannot verify is not automatically false, but do not enshrine it at an ancestor. Drop it
and say so.

Dispatch this as one subagent per heading (`sonnet` is enough), each returning the canonical text
plus what it fixed, what it dropped, and what was false in which copies. Read their evidence, not
their verdicts: spot-check at least one claim per report with your own control, because a
hand-rolled detector reports what its pattern can see, not what is true.

## 3. Converge - compose the correct text

The canonical is not "the winning variant", it is the text that survives verification. Take the best
lines from any copy, fix what is wrong, drop what you could not confirm.

Two rules for what you write:

- **State the applicability TEST, never a dated census.** "Does this repo have a `pyproject.toml`
  and a generated Makefile? Check the repo in front of you" stays true. "Verified <date>: A, B and C
  do not" is wrong the moment the tree grows, and the date makes it look checked.
- **When the source of truth is generated, point at it instead of copying it.** A table of make
  targets drifts by construction; `make help` reads the Makefile and cannot. Prefer the pointer.

## 4. Lift - to the common ancestor, without a double heading

Judge the trim by the REACHABILITY INVARIANT only (`bitranox:meta-dream-tree` ->
references/dream-passes.md): a covering rule at an ANCESTOR DIRECTORY, delivered as always-loaded
text. Git tracking plays no part - not tracked-vs-ignored, not the remote, not who else could clone
it. Those decide whether an edit needs a commit, never whether a rule reaches context.

Three guards the mechanical version gets wrong:

- **The invariant is tested per FILE, not per GROUP.** A group's members can straddle the covering
  ancestor's subtree - some sit under it, some do not. Check each member's own directory against
  the chosen covering ancestor before trimming that member; one check for "the group" (or for
  where most of it lives) trims outliers too, and for a member outside the subtree the covering
  rule is only a SIBLING that never loads there, so it loses guidance with nothing replacing it.
- **No chain may end up holding the heading twice.** Before lifting a variant to `T`, check whether
  any NON-MEMBER file under `T` still carries that heading - members do not count, the lift strips
  them. Seed the check with headings the target ALREADY holds from an earlier pass, or you will
  append a second section of the same name to a file that has one.
- **Preserve the repo-specific rows.** A section is rarely all boilerplate. Keep the genuinely local
  parts under a DIFFERENT heading (`## Make targets specific to this repo`) so they survive and
  cannot collide with the lifted one.

Relevance still gates the target even though git does not: never lift a narrow rule into a tier that
loads where it is irrelevant. A shared rung whose children mostly do not use the content is the
wrong home even when it is the technical common ancestor.

## 5. Verify the result

Snapshot every file first (a copy OUT of the tree - `git checkout` restores only tracked files, and
`git status --porcelain` cannot tell a gitignored file from a clean one). Afterwards:

- Re-run the walk: the heading appears exactly once per chain.
- Confirm with a CONTROL that your checker can still find something that IS present, or a zero
  proves nothing.
- Spot-read one member file end to end for a mangled structure or an orphaned anchor link.

## Rationalizations

| Excuse                                            | Reality                                                                                   |
|---------------------------------------------------|-------------------------------------------------------------------------------------------|
| "The most-copied version is the right one"        | It is usually the oldest. Verify against the system, not the other copies.                |
| "They are all the same section, just lift one"    | Package-name variance is not liftable at all, and drift means most copies are then wrong. |
| "The ancestor is untracked, so I should not trim" | Git never gates a trim. Only the reachability invariant does.                             |
| "I will note which repos it applies to"           | A census in always-loaded text rots silently. Write the test.                             |
| "grep found them all"                             | The session grep skips gitignored files without saying so. Walk, or use `grep_all`.       |
| "The section is boilerplate, delete it whole"     | Check for the two or three genuinely per-repo rows first; they are easy to lose.          |

## Common mistakes

- Lifting before verifying, so a false line gets promoted to bind every repo below.
- Computing the common ancestor from the subtree you happened to be looking at, rather than from
  every member path.
- Leaving a heading at both an ancestor and a descendant, so a reader meets it twice with
  conflicting content.
- Reporting "0 remaining" from the same detector that under-counted going in.
