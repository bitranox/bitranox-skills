# skill-writer checklist - meta-dream-tree (2026-10-05, exit codes, transcript offer, lexical dedup)

`due`/`should-promote` answer no with exit 1; session-review lists every other unconsumed
transcript and reads one with `--transcript`; a clean dedup_scan run is followed by a semantic
pass; the local audit pass gives the runnable `audit_local.py check` line; run-python.sh's CLI
could-not-run exit is 2.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Test approach: retrieval - seven questions whose answer
      depends on the changed behaviour, answered ONLY from pasted passages, with a direct quote or
      NONE, plus a "Skill gaps" section.
- [x] Scope: SKILL.md "When to run", step 4, step 5; dream-core.md "Capture-first" and the
      corroboration paragraph; dream-passes.md removal policy and local audit pass;
      meta-dream-crosstree step 0 (its own checklist). No frontmatter change.
- [x] Inherited-context route: the arms are pasted passages on the inert `bitranox:baseline-probe`
      type told not to invoke a skill, so both arms are a text check of the passages, not of the
      installed skill.

## RED
- [x] Old passages (cut by marker text from the files), haiku, inert probe type:
      Q1 `due` exit 1: right action, but quoted only "`not-due` never suppresses capture" - no
      line covers the exit code. Q2 `hold` exit 1: inferred, listed as a gap. Q3 the 30-entry
      offer: "you must read all 30". Q4 reading one listed transcript: "Do not manually select
      from the 30", plain session-review. Q5 zero dedup candidates: "the tree is free of
      duplicates", nothing further in step 4. Q6 audit_local: no runnable line (gap). Q7: exit 3.
- [x] Ground truth for Q6 and Q7: `audit_local.py --root <dir> --no-personal` exits 2 with
      argparse "invalid choice"; `audit_local.py check --root <dir> --no-personal` runs (exit 0).
      Q7 follows the run-python.sh CLI change to exit 2 in the same wave.

## GREEN
- [x] New passages, same model and questions: Q1 quotes "that 1 is the answer no, not a
      failure"; Q2 quotes "prints `promote` with exit 0 or `hold` with exit 1, an answer either
      way"; Q3 "The list is an offer, not a quota"; Q4 the `--transcript <path>` pair with "the
      SAME path"; Q5 "A clean scan is a clean LEXICAL scan, never a clean tree ... Zero candidates
      never skips this pass"; Q6 `audit_local.py check --root <tree> --no-personal` with its home;
      Q7 exit 2.
- [x] GREEN diffed against RED in both directions: Q1, the only RED answer that was right, stayed
      right; nothing a baseline answered was lost.
- [x] Skill gaps asked for in both arms. GREEN reported: what `<tree>` means in the audit line -
      closed, the line now reads `--root <anchor> --no-personal` (the tree's top dir); what counts
      as a "manual dream" - declined, untouched pre-existing text outside this change; whether the
      unread count is reported - declined, the passage says "report how many the run left
      unread"; a CLAUDE.md section the probe could not find - declined, not part of the passages.
- [x] Every stated behaviour checked against the script: dream_state exits and the offer are
      pinned by tests in tests/test_dream_state.py that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] ASCII only in every added line.
