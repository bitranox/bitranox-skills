# skill-writer checklist - compuse-toolbox (2026-10-05, doc sync for the rank-181 script fixes)

The `pushcheck` and `ci_wait` rows and the `grep_all` note now state the behaviour the scripts have:
pushcheck scans commit messages and names unscanned binary files, ci_wait refuses a sub-5-second
`--interval` and says when the deadline cut a settle short, grep_all skips every `.venv*`
directory and never counts a named file as missed.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed behaviour, answered ONLY from pasted passages, with a direct quote or NONE.
- [x] Scope: the three passages that describe the changed behaviour; no frontmatter change.
- [x] Inherited-context route: the arms are pasted text on the inert probe type told not to
      invoke a skill, so the answer is a text check of the passages, not of the installed skill.

## RED
- [x] Old passages (extracted from the file, not retyped), haiku, inert probe type:
      Q1 pushcheck, clean diff, home path in the commit MESSAGE: passes, "the commit message is
      not scanned" (wrong).
      Q2 pushcheck, binary file beside clean text: NONE.
      Q3 pushcheck, binary-only range: refusal, through the EMPTY-range sentence (right verdict,
      wrong reason).
      Q4 ci_wait `--interval 1`: NONE.
      Q5 ci_wait, green too close to the deadline for the full settle: NONE.
      Q6 grep_all, a gitignored file named on the command line: NONE.
      Q7 grep_all, `.venv-3.12` searched?: NONE.
- [x] Skill gaps asked for: the RED reply listed Q2 and Q4-Q7 as unaddressed.

## GREEN
- [x] New passages, same model and questions:
      Q1: "on a public repo a finding in a message refuses even a removal-only range".
      Q2: "A binary file's content is never scanned, so each one is NAMED instead (the JSON
      `skipped` list, a `not scanned` line)".
      Q3: "a range that adds only binary content is refused, never called clean".
      Q4: "an `--interval` below 5 seconds is refused (exit 2)".
      Q5: "A green seen so close to the deadline that the settle was cut short, or never
      re-polled at all, is still reported as success, with the summary saying so."
      Q6: "A file you NAME on the command line never counts as missed, since a gitignore-aware
      search reads a file it is given."
      Q7: "or any `.venv*` directory".
- [x] GREEN diffed against RED in both directions: Q3's refusal stayed a refusal, now for the
      stated reason; no answer the baseline had was lost.
- [x] Skill gaps asked for again: none reported.
- [x] Every stated behaviour checked against the script it describes, and each script change is
      pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Tables canonical (`reformat_tables.py --check` reports the file unchanged).
