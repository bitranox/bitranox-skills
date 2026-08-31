# checklist-20260831-open-work

Change under test: the handover splits into two artifacts. `handover.md` keeps the moment;
`OPEN-WORK.md` becomes the ranked standing backlog, reconciled BEFORE the handover is overwritten,
and re-surfaced every session by `session-start.py`.

## PLAN

- [x] Skill type: discipline. The text prescribes a procedure and the failure is a rule not
      followed under pressure, so the test approach is pressure scenarios, not retrieval.
- [x] Scope: self-contained `SKILL.md` plus one hook function. No new reference file.

## RED

- [x] Scenario: a session that finished one small user-requested task holds an outgoing handover
      whose "Deliberately not done" section carries five standing items with their counts. It must
      write the new handover.
- [x] Inherited-coverage checked with `redcheck.py --corpus-cascade .`: 957 documents, verdict
      INHERITED COVERAGE. Adjudicated as a false positive on the shared-terms list, which is
      function words and the scenario's own subject nouns (`filename`, `listed`, `previous`,
      `sample`, `toolbox`, `jsonl_grep`). Confirmed by grepping the whole cascade and all 949 fact
      bodies for the actual lesson keywords - `ordered by importance`, `top-ranked`, `re-ranked`,
      `never by how recently` - which returns nothing. The ranking rule is taught nowhere on this
      machine, so the arm can fail honestly. The carry-forward half IS taught by
      `feedback-audit-a-do-not-delete-record-before-overwriting-it-not-after`, so that half is
      evidenced by a text check of the artifact rather than behaviourally.
- [x] RED on haiku FAILS as predicted: the five items collapse to a bare list, the user's verbatim
      directive, its 2026-08-27 date and its "no decision recorded since 2026-08-28" note are all
      dropped, and the next-action slot reads "No immediate action required." Its own gaps section
      reports "Previous handover is not being carried forward."
- [x] RED on sonnet largely resists, and still fails the ranking half: its next action offers an
      owed learning capture first and the 3-day-stale user directive second, with no reason given
      for the order. Recorded rather than escalated - a partial RED is the result.

## GREEN

- [x] Both arms re-run against the rewritten text, same scenario, only the governing text changed.
- [x] haiku GREEN: all five items reach `OPEN-WORK.md` with their sizes, the user directive is
      rank 1 with `USER:` origin and its real date, and the next action is the top-ranked item with
      an explicit "This item is top-ranked ... No override reason needed."
- [x] sonnet GREEN: all five carried, and it refuses to fabricate the three missing dates.
- [x] Both arms asked for a `Skill gaps` section; both lists recorded and worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (haiku): invents first-raised dates for three items, annotating one "pure placeholder".
      CLOSED - the text now prescribes today's date with a `?` plus `first seen here`, and states
      that an estimated date silently resets the only signal that makes a long-carried item
      conspicuous.
- [x] GAP (sonnet): "size is the count that decides rank" never states the direction, so it ranked
      a 206-item internal sweep ABOVE the user's 88-target directive. CLOSED - rank is now an
      ordered rule with origin first and size as a tiebreak, and it names that inversion as "the
      failure in a new costume".
- [x] GAP (sonnet): reaches for `(unknown)`, a form the parser does not accept. CLOSED by the same
      date rule, which prescribes the exact string to write.
- [x] GAP found by dogfooding the rule against the seeded file: a `USER:` item the user themselves
      deferred, and a blocked item given a third invented origin. CLOSED - deferred `USER:` items
      rank below live ones and above every `FOUND:` one, and blocked is a value for `open:`, never
      an origin.
- [x] DECLINED: haiku's GREEN handover pairs the required per-item pointer with a one-line summary
      of the backlog. The rule already forbids a summary; tightening it further would trade the
      pointer's readability for a violation that costs nothing when it happens.
- [x] GREEN diffed against RED in both directions. Nothing the baseline produced is missing from
      GREEN: RED's handover content is a subset, with the standing items relocated rather than
      dropped.
- [x] Each fix verified by quote-back on the least inferential tier. Four contested questions,
      four direct verbatim quotes, no NONE: origin outranks size, the `?` date form, blocked keeps
      its rank, `size: unknown` is usable.

## Mechanical checks

- [x] `description` measured with `len()`: 509 characters, under the 1024 cap.
- [x] Both derived artifacts regenerated after the description changed: `skill_triggers.json`
      (82 skills) and `docs/skills.md`.
- [x] Hook tests written BEFORE the implementation: 5 of 8 failed against the unmodified
      `session-start.py`.
- [x] Both silence tests proven non-vacuous by mutation. Removing the empty-list guard fails
      `test_open_work_with_no_open_items_is_silent`; making the except path return a block fails
      `test_open_work_absent_is_silent`. `__pycache__` cleared around each, and the restore is from
      a copy taken first, not from git.
- [x] The `?` date form has its own test, RED-verified: the original regex rejected it, so the
      honest form would have been the invisible one.
- [x] Whole hook suite with CI's dependency set: 2408 passed, 1 skipped, 1 xfailed.
- [x] End-to-end against this repo: the block renders 11 items, prints ages of 3, 4 and 30 days,
      caps at 5 with "and 6 more", and the whole essentials context is 2058 bytes against the
      3500-byte budget.
- [x] No session narrative, operator instructions or scratch paths in the skill or this artifact.
- [x] No address, MAC, hostname or private path added to the skill.
