# skill-writer checklist - compuse-git (trial merge in the object store; checkout discards work)

Change: two Quick reference rows. (1) `git merge-tree --write-tree` answers "will this branch
still merge" without touching the checkout. (2) `git checkout -- <file>` discards ALL uncommitted
work in that file, which makes it the wrong undo for an experimental edit.

## PLAN

- [x] Skill type: reference (a table of git mechanics). Test approach: run the commands and
      observe, then a text check of the artifact.
- [x] Checked against EVERY shipped skill: `grep -rn "merge-tree\|merge_tree" skills/` returns
      nothing anywhere, and no skill states what `git checkout --` discards. compuse-git owns git
      mechanics.
- [x] Row 2 is the git half of a lesson whose procedural half belongs elsewhere: the
      restore-from-a-copy discipline is filed against the skill that PRESCRIBES mutation
      (`process-review-enhance-code-quality`), and this row states the underlying git behaviour on
      its own, since it applies to any experimental edit.

## RED

- [x] Behavioural RED is NOT available on this machine for either row. Both lessons already sit in
      the always-loaded memory store:
      `reference-trial-merge-in-the-object-store-to-answer-whether-a-branch-is-stale.md` and
      `feedback-restore-an-experiment-from-a-copy-not-from-git-while-the-work-is-uncommitted.md`.
      Route taken: TEXT CHECK of the artifact.
- [x] Worth recording: `redcheck.py --corpus-cascade .` reported the merge-tree scenario CLEAN.
      That was wrong, and the tool says why in its own output - it compares distinctive terms and
      cannot see a paraphrase. The stored fact says "trial merge in the object store" where the
      scenario said "merge cleanly", so the vocabularies do not overlap. A clean redcheck result
      means NOT CAUGHT, never absent; the fact was found by listing the store instead.
- [x] Both merge-tree claims MEASURED on git 2.53.0 in a throwaway repo rather than taken from the
      queue entry:
      - clean merge: exit 0, prints a tree sha
      - HEAD, `show-ref` and `status --porcelain` all byte-identical before and after (the row's
        central claim, that nothing is touched)
      - `git grep <tree-sha>` reads the merged result: `<tree>:other.txt:2:feature_only_symbol`
      - conflicting merge: exit 1, printing the tree sha then the stage entries naming the
        conflicted path

## GREEN

- [x] Text check row 1: states the version floor (2.38+), what it writes and prints, that no ref,
      index or working tree changes, the exit behaviour on conflict, the alternatives it replaces,
      and the follow-up step.
- [x] Quote-back for "a clean merge is not a correct merge": "A conflict-free merge can still be
      semantically WRONG, so inspect the result rather than stopping at the exit code:
      `git grep <pattern> <tree-sha>` searches the merged tree directly."
- [x] Quote-back for row 2's silent-loss property: "The loss is silent in the direction that looks
      like success: the file drops out of `git status`, which reads as clean."

## REFACTOR

- [x] Row 1 says "prefer it to the alternatives in reach", naming the scratch worktree and the
      aborted `--no-commit` merge, so a reader who already has a habit sees why to change it.
- [x] Row 2 names the two situations that make the undo lossy (a feature mid-cycle, an edit made
      to prove a test can fail) rather than stating the git behaviour abstractly, and closes with
      the boundary: git is a correct restore only for work already committed.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] Placeholder names only (`<base>`, `<branch>`, `<file>`, `<pattern>`, `<tree-sha>`).

## Deliverables

- [x] Two Quick reference rows in `SKILL.md`. No script, so no `tests/` change.
