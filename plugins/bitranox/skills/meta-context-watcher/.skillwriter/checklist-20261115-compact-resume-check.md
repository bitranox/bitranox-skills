# checklist - check a resumed checkpoint before taking its next action

The compact-resume paragraph said "Take its exact next action at once". It now checks the next
action against the compaction summary and `git log`/`git status` first, continues from the
summary when the action is already done, and leaves a checkpoint the summary never mentions (a
tracked repo-root `handover.md` another session wrote) alone. The bold lead is narrowed to "as of
when it was written", and the paragraph is reflowed to the file's width.

Decisions: d-20261115-5ef6e29e

## RED

- [x] Skill decisions read first: none for this skill.
- [x] Both failure shapes are real: a queued report of a checkpoint whose next action had been
      committed and pushed before the compaction; and in THIS session the resume block handed
      back the worktree's tracked `handover.md`, written by another session about unrelated work.
- [x] Coverage probe on the pre-edit paragraph, opus and haiku: both took the checkpoint's stale
      next action literally (quoting "Take its exact next action at once").

## GREEN

- [x] Same question on the edited paragraph, opus and haiku: both checked the summary and git
      first, marked the checkpoint STALE and continued from the summary's step, quoting the new
      sentence verbatim.

## REFACTOR

- [x] Declined (opus): "STALE means two things" - in both branches it marks the FILE as read
      (`# STALE - read <date>, work continued`, the exact line the resume block prescribes in
      `hooks/compact-resume.py`), never whether the action ran.
- [x] Declined (opus, haiku): "summary and git disagree" - git is the ground truth the paragraph
      names beside the summary; a disagreement is ordinary verification, not a new rule.
- [x] Not changed here, reported instead: `hooks/compact-resume.py` itself tells the reader to
      resume "starting with its exact next action"; that hook is outside this change.
- [x] Width and fence check over the added lines printed nothing.
