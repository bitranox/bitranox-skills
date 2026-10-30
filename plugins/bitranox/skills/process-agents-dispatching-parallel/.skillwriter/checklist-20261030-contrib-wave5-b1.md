# Review checklist: process-agents-dispatching-parallel, queued contributions (2026-10-30)

Entries covered:

1. Landing uncommitted worktree diffs: one integration worktree with `git apply --3way`, then a
   byte-compare of every single-owner file - new paragraph in "Review and Integrate".
2. A fan-out large enough to reach the usage limit: dispatch release-critical and longest items
   in a first wave - new paragraph in "Dispatch in Parallel".
3. A stopped measurement lane's numbers live in its evidence dir and transcript - new paragraph
   in "An agent that stopped mid-task left no report".
4. `isolation: worktree` agents branch from origin's default branch, not local HEAD - new brief
   item pointing at bitranox:git-worktrees Step 1a (which already holds the mechanism and the
   `worktree.baseRef` fix) plus the per-worktree `merge-base --is-ancestor` check.

## Evidence

- [x] The integration recipe was run end to end in a scratch repo: two worktrees with uncommitted
      changes (a modified shared file, a modified single-owner file, two new untracked files);
      `git add -N . && git diff --binary HEAD > w.patch` per worktree, `git apply --3way` of both
      into a third worktree: both applied, the shared file held both edits, and `cmp` of every
      single-owner file against its owner's copy matched. `git diff --name-only HEAD` after
      `add -N` listed new, modified and deleted files alike.
- [x] Entry 4's mechanism is already documented and was read: git-worktrees SKILL.md, Step 1a,
      "Native tools branch from origin's default branch, not from local HEAD". The new item
      points there instead of restating it.
- [x] RED as a text check on the pre-edit file: `apply --3way|byte for byte` 0 hits,
      `first wave` 0, `evidence directory` 0, `merge-base --is-ancestor` 0. After: 2, 1, 1, 2.
- [x] GREEN probe (`bitranox:baseline-probe`, haiku, edited excerpts pasted, five questions,
      quote-back required): all four dispatch questions answered with a direct quote of the new
      text and the intended action (push or fast-forward then check each worktree; first wave of
      the three release items plus the longest; evidence dir and transcript before a re-run;
      add -N / diff / apply --3way / cmp per single-owner file).
- [x] Skill gaps from the probe, each decided:
      - "`add -N` changes the agent worktree's index; deleted files and owner counting not
        stated" - CLOSED: the text now says a deleted file must be absent from both, and that
        `git diff --name-only HEAD` after `add -N` gives each agent's list to count owners from.
      - "Push or fast-forward: which is preferred" - declined: either holds; git-worktrees Step
        1a (pointed to) also offers `baseRef: head`.
      - "'Long' is not defined" - declined: a judgement the dispatcher makes per fan-out.
      - "Where the transcript lives" - declined: covered in the same section under "Structured
        output must be harvested from the TRANSCRIPT" (named vs unnamed agent locations).
- [x] Width and fence check over the added lines printed nothing after one overlong line was
      re-wrapped; paragraphs after each insertion read: no re-bound reference.
- [x] ASCII only; front matter parses with `yaml.safe_load`; tables canonical.
- [x] No private paths, hosts or names.
