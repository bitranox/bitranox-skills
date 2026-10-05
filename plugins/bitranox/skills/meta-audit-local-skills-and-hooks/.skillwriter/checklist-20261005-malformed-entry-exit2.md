# skill-writer checklist - meta-audit-local-skills-and-hooks (2026-10-05, malformed entries + exit 2)

`audit_local.py check` reports a wrong-shaped hook entry inside a loadable settings file as
`settings-malformed-entry` and keeps checking the file's other registrations; `settings-unparseable`
is left for files Claude Code rejects whole (not JSON, not UTF-8, an event whose value is a
string). Both verbs exit 2 for a `--root`/`--home` that is not a directory and for a directory the
walk could not list. The Step 2 passage now states all three.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - four questions answered ONLY from the
      pasted passage, each with a direct quote or NONE, on the inert probe type pinned to haiku.
- [x] Scope: the Step 2 check list and exit-code paragraph; no frontmatter change.

## RED
- [x] Old passage: Q1 (malformed Stop beside a good PreToolUse) silent on the malformed entry;
      Q2 (`targets --root` typo exit) NONE; Q3 (unlistable dir exit) answered 1, which the code no
      longer returns; Q4 (which shapes are unparseable) NONE.
- [x] Skill gaps asked for: the four silences above, plus no finding name for a missing-file
      registration.

## GREEN
- [x] New passage, same model and questions: Q1 `settings-malformed-entry`, other registrations
      still checked; Q2 2; Q3 2; Q4 the three whole-file shapes - each by direct quote.
- [x] GREEN diffed against RED in both directions: nothing RED answered correctly was lost.
- [x] GREEN's gaps (no code name for a missing-file registration; "every hook in one is dead"
      read as possibly a fourth condition) closed in the text: `registration` named, the
      consequence split from the condition list by a semicolon.
- [x] Every stated behaviour checked against `scripts/audit_local.py` and
      `hooks/harness_checks.py` (`scan_hook_registrations`) and pinned by
      `tests/test_audit_local.py`.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] No table row changed.
