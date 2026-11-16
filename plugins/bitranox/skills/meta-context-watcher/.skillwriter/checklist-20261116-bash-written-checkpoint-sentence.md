# checklist - the step 4 sentence on a Bash-written checkpoint follows the new resume

Step 4 ("A live peer's `handover.md` is not yours to replace") said the compaction resume "finds
one written through Bash only at the repo root". Since the resume attributes a checkpoint by the
session's own Write/Edit (decision d-20261116-8f504808), a Bash-written file is listed with path
and age, never handed back as the session's own. The sentence now says that. The context
watcher's save request in hooks/context-watcher.py carried the same old clause and is corrected in
the same change.

Decisions: d-20261116-8f504808

## RED

- [x] Text check on the pre-edit step 4: it states "finds one written through Bash only at the
      repo root", which the shipped hook (compact-resume.py, Write/Edit attribution) no longer
      does: a Bash-written file at the repo root is listed, not handed back.

## GREEN

- [x] The sentence now reads "one written through Bash it only lists, never as this session's",
      matching the resume paragraph W5 rewrote and its tests in hooks/tests/.
- [x] ASCII only, line width unchanged.
