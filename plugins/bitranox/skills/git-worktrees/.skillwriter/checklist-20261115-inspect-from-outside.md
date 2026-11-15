# skill-writer checklist - git-worktrees (2026-11-15, inspect a removable worktree from outside)

- [x] Receipt issued; Step 0b `show` run: no rejected or removed decision; the live rules
      d-20261108-f33703e1, d-20261108-bdfba564 and d-20261115-bdcc7ef3 keep their anchors.
- [x] Premise checked: Step 4 told the reader to list ignored files "inside it", which invites a
      `cd` into the worktree; in an agent harness that `cd` persists, so the removal ran from the
      directory it deletes (Windows refuses it; elsewhere the next git call exits 128 in a
      deleted cwd). The queued incident is that sequence.
- [x] RED (no skill, opus and haiku `baseline-probe`): asked directly, both chose `git -C` and
      named the deleted-cwd hazard. The defect is in the skill's own wording, so the change
      replaces "inside it" with `git -C <worktree> status --ignored --short` and adds one
      paragraph rather than a longer explanation.
- [x] GREEN (new Step 4 excerpt, opus and haiku quote-back): both answered `git -C` with absolute
      paths, quoting the new paragraph.
- [x] Gaps declined: both noted `git -C` and the `( cd ... )` subshell are both allowed - that is
      intended; neither persists the cwd.
- [x] Width and fence check over the added lines printed nothing.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-fa7c46eb
