# skill-writer checklist - meta-adopting-external-skills (2026-09-26, doc sync for the 7.25.6 script fixes)

A failed run removes its half-written skill folder and restores THIRD_PARTY_NOTICES.md; npm's `SEE LICENSE IN <file>` is read.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed behaviour, answered ONLY from pasted passages, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.
- [x] Inherited-context route: the arms are pasted text on an inert probe type told not to invoke
      a skill, so the answer is a text check of the passages, not of the installed skill.

## RED
- [x] Old passages (built from the porcelain word diff, not retyped), haiku, inert probe type:
      Q13 failure part-way: the half-written folder: NONE (old text: "never removes anything").
      Q14 npm SEE LICENSE IN TERMS: NONE.
- [x] Skill gaps asked for: the RED reply listed every question above as unaddressed or
      only partly covered.

## GREEN
- [x] New passages, same model and questions:
      Q13 failure part-way: the half-written folder: "a run that fails part-way removes the skill folder it started and puts `THIRD_PARTY_NOTICES.md` back".
      Q14 npm SEE LICENSE IN TERMS: "npm's `SEE LICENSE IN <file>`, whose file it reads".
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
