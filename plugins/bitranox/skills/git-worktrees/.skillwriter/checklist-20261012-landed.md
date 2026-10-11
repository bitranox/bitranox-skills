# skill-writer checklist - git-worktrees (Step 4: did the work land? landed.py)

Change: a new Step 4 introduces `scripts/landed.py`, which says from content whether a worktree's
files and a branch's commits are already on the target branch; the build-cache cleanup becomes
Step 5, and its Quick Reference row says so. A new row points a reader about to discard a dirty
worktree or `branch -D` a squashed branch at landed.py. The description adds that trigger.
`wtclean.py`'s dirty refusal names landed.py.

## PLAN

- [x] Skill type: technique with a bundled tool (a check to run before a destructive step).
- [x] Scenario drafted before editing: eight leftover worktrees whose work landed partly squashed
      and partly as hand-copied uncommitted files; decide which can go without losing anything.
- [x] Scope: one new section in an existing skill, one Quick Reference row, one description
      clause; a new script with sibling tests.

## Script

- [x] `scripts/landed.py` has sibling tests, `tests/test_landed.py` (19 cases), all on real
      repositories driven through the CLI; the whole skill suite passes (126).
- [x] Every test seen to fail: a 10-arm mutation battery (history lookup removed, multiset
      matching made a set, the index lock allowed, lines no longer deciding the branch verdict,
      local deletion always landed, blank lines counted, patch-equivalence never counted,
      untracked files skipped, changelog ignored, local main dropped from the defaults) was
      KILLED arm for arm, each by the test written for it, baseline green before and after.
- [x] Read-only: git runs with `--no-optional-locks`, pinned by a test asserting the index
      bytes and mtime are unchanged after inspecting a dirty worktree.
- [x] The squash premise measured, not assumed: on a squash-merged branch `patch_equivalent` is
      0 of 2 while every added line is present.
- [x] No third-party import; stdlib only.

## RED

- [x] Inherited-context check: the answer (a content-based landed check) is not taught anywhere a
      dispatched agent inherits; the RED ran as `bitranox:baseline-probe`.
- [x] RED, haiku, pre-change Step 4 (then the cache step): no instrument; it hand-rolled six or
      more commands per worktree (`diff --exit-code`, `cat-file`, `cmp`, `merge-tree
      --write-tree`, `cherry`). Gaps verbatim: "The text does not say how to decide whether
      uncommitted work is already on master. Section 1 is my own method, not the skill's." and
      "The text does not say to check for landed work before using that flag."

## GREEN

- [x] GREEN, sonnet and haiku: both run `landed.py` on the worktree and on the branch, read the
      exit code alone, and refuse `--discard-uncommitted` and `branch -D` on a 1; both quote "Only
      a 0 makes `--discard-uncommitted` safe" and the cherry/squash sentence.
- [x] Every dispatch asked for a "Skill gaps" section; the lists are worked below.
- [x] GREEN diffed against RED in both directions: RED's fetch-first point and its warning that
      `git branch -d` refuses a squashed branch are kept (the fetch advice is in the text; the
      `branch -D` case is named in the new Quick Reference row). Nothing RED produced is lost.

## REFACTOR

- [x] Gap (sonnet) "the line test can pass with lines in other places" - CLOSED: "It is
      evidence, not proof: a line counts wherever in the file it sits". Quote-back, haiku: Q4.
- [x] Gap (sonnet) "files landed but branch not" - CLOSED: "A worktree is landed only when its
      files AND its commits both are." Quote-back: Q1.
- [x] Gap (haiku) "gitignored files are not covered, yet removal deletes them" - CLOSED, after a
      probe: a plain `git worktree remove` deleted a worktree holding only an ignored file (rc 0)
      and refused one holding an untracked file (rc 128), so the sentence says removal deletes
      ignored files even without `--discard-uncommitted`. Quote-back: Q2.
- [x] Gap (haiku) "what exit 2 means for the decision" - CLOSED: "a 2 is not a 0". Quote-back: Q3.
- [x] Gap (both) "how to save what a 1 names" and "what the output looks like" - CLOSED: "commit
      it on the branch or copy it out of the checkout", and the output sentence. Quote-back: Q5.
- [x] Gap "which directory to run `scripts/landed.py` from" - DECLINED: the same convention as
      `wtclean.py` in Step 5, stated as "in this skill's directory".
- [x] Gap "how to tell whether an ignored file is regenerable" - DECLINED: that is the reader's
      judgement; the text says to copy out any they need.
- [x] Gap "causes of exit 2" - DECLINED: listed in the script's own docstring and `--help`.
- [x] Gap "a file master deleted after the work landed" - DECLINED: covered by the history
      sentence, since the commit that held the landed bytes is one that touched the path.

## Quality

- [x] Description measured: 572 characters, under the 1024 cap; derived `skill_triggers.json`
      and `docs/skills.md` regenerated.
- [x] No session narrative or private provenance in the change or this artifact.
- [x] No address, hostname or private path added.
