# skill-writer checklist - meta-consolidate-claude-md (2026-09-26, doc sync for the 7.25.6 script fixes)

The largest variant's share is of the group's copies, matching claudemd_variance.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed behaviour, answered ONLY from pasted passages, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.
- [x] Inherited-context route: the arms are pasted text on an inert probe type told not to invoke
      a skill, so the answer is a text check of the passages, not of the installed skill.

## RED
- [x] Old passages (built from the porcelain word diff, not retyped), haiku, inert probe type:
      one file holding a heading twice (two bodies) plus a second file with the first body:
      share over files or copies, and what X: NONE (a separate probe on this one question).
- [x] Skill gaps asked for: the RED reply listed every question above as unaddressed or
      only partly covered.

## GREEN
- [x] New passages, same model and questions:
      same question: over copies, 67 percent (2 of 3), quoting "the largest variant's share of
      the group's copies".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right;
      nothing a baseline answered was lost.
- [x] Skill gaps asked for again. One reported: what the license gate does after reading a
      `SEE LICENSE IN` file - declined, the full sentence in the file continues "and one copyleft
      id rejects" and lists an unrecognised license text as a stop; the probe saw a cropped
      excerpt.
- [x] Every stated behaviour checked against the script it describes, and each script change is
      pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Tables re-padded by the formatter where a row changed (`reformat_tables.py --check` clean).
