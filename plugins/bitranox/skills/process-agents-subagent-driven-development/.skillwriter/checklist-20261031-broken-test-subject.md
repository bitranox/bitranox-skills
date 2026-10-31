# skill-writer checklist - process-agents-subagent-driven-development (broken test: decide by subject)

- [x] Change: implementer-prompt.md - new paragraph before "How to escalate": a STOP rule about
      existing tests asserting the old behaviour (in the template or the brief's constraints)
      fires only when the test is ABOUT the changed behaviour; a test that passed only because
      the bug masked an incidental input keeps its subject and expectation, the input is pinned
      (or a fitting one passed) with a comment, and it is listed in the report; if the pinned
      test still fails, STOP. SKILL.md - one paragraph after "A task that ADDS or TIGHTENS a
      refusal" telling a controller who hand-writes such a STOP constraint to add the subject rule.
- [x] Coverage check before editing: grep of the skill dir for "existing test", "old behaviour",
      "incidental", "masked", "pin the" found no rule deciding this case (SKILL.md:123 covers a
      task that tightens a refusal, not a fix that unmasks an input).
- [x] RED (haiku, pre-edit STOP list plus a "STOP if an existing test asserts the old behaviour"
      constraint): chose (a) STOP and report BLOCKED for a QR scaling test broken only because
      the fix stopped rounding away a default offset, quoting the constraint, and stated "The
      test's subject being QR scaling does not change that".
- [x] GREEN haiku (offset case, two tests): scaling test -> pin `offset_along=0`, keep the
      expectation, quoting "Keep that test's subject and its expectation: pin the incidental
      input ..."; rounding test -> STOP, quoting "STOP only when the failing test's subject is
      the old behaviour itself."
- [x] GREEN opus (calibration case at scale 0.9, two tests): calibration test -> pass the length
      that fits, expectations unchanged; rounding-down test -> STOP. Same quotes.
- [x] Gaps closed after GREEN: (1) opus asked whether the template's reading overrides a
      controller's STOP constraint -> the rule now says "in this template or in your brief's
      constraints"; (2) haiku guessed what to do when the pinned test still fails -> "If the
      pinned test still fails, its subject is affected after all: STOP."
- [x] Final quote-back (haiku) on the final text, three questions: Q1 no STOP on the scaling test
      (quoted the "in this template or in your brief's constraints" sentence), Q2 STOP when the
      pin does not restore it (quoted), Q3 STOP on the rounding test (quoted). No new undecided gap.
- [x] Tiers: haiku x3 (RED, GREEN, final), opus x1 (GREEN); 5 test cells across the GREEN arms.
- [x] Gaps declined: BLOCKED vs NEEDS_CONTEXT when the rounding test also has a docs-only remedy
      (the existing "fixed two ways" bullet decides it, implementer-prompt.md STOP list);
      choosing between pinning and a fitting input (judgement left to the implementer, both
      keep the expectation); adding a test for the pinned-away input (the fix's own task tests
      cover the new behaviour, owned by bitranox:process-test-driven-development); report format
      and partial work while BLOCKED (covered by the template's Report Format section); a test
      asserting the old behaviour that stays green (cannot happen once the behaviour changed).
- [x] Width and fence check over the 18 added lines: none over 100 columns, no non-ASCII; no fence
      touched. reformat_tables.py --strict on SKILL.md: Unchanged.
- [x] Paragraph after each insertion read: "Plan mode must have ended" and "How to escalate" carry
      no back-reference that now binds to the new text.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
