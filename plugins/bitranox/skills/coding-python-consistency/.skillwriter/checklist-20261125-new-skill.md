# skill-writer checklist - coding-python-consistency (2026-11-25, new skill)

A new Python companion to `bitranox:coding-consistency`: a table of standard-library spellings
that read as equivalent and return different results, four shapes that leave one place to write
(one rule function, one population and window type, one conversion per unit, one default), what
Python and pyright do not report, and the searches that feed the generic review. No scripts.

Decisions: d-20261125-fd4283d3, d-20261125-f3dcd01c, d-20261125-9bc0faac

- [x] Receipt fresh (armed for the session, skill-writer loaded in this agent). Step 0b before
      the first edit: `skill_decisions.py show coding-python-consistency` reports no skill, the
      skill did not exist. After the ledger was written, `skill_decisions.py check
      coding-python-consistency` reports 0 findings.
- [x] Not mirrored: the family is new and ships only from this marketplace.
- [x] Skill type: reference plus technique (a measured table, shapes, searches); test is
      application together with the generic skill, on the scenarios and with the probe set-up
      recorded in `coding-consistency`'s checklist of the same date.

## Commands executed (CPython 3.14.4, standard library; pyright 1.1.414)

- [x] Every row of "Same value, two results" run and the printed values compared with the
      table: quantiles exclusive 38.95, inclusive 38.05, index 39.0 on 1.0 to 40.0; median 2.5
      and 3; `round(2.5)` 2 and half-up 3, `round(0.5)` 0; `int(0.29 * 100)` 28 and `round` 29;
      `-7 // 2` -4 and `int(-7 / 2)` -3; `1999 // 1000` 1 and `1999 / 1000` 1.999; the four
      case and pattern rows.
- [x] The four code blocks extracted from the SKILL.md into one module and run: the doctest of
      `is_urgent` passes, `check_entry_points_agree()` and `check_one_default()` pass,
      `cost_cents(0.3, 5.0)` is 3 and `round(0.3 * 5.0 / 60 * 100)` is 2.
- [x] pyright in its default mode on a class with a write-only attribute: 0 errors, 0 warnings.
- [x] A keyword-only parameter without a default added to a function: the unedited call raises
      `TypeError`.
- [x] The candidate grep run on a test package with planted pairs: every planted pair listed.
      The public-name diff line run on a scratch repository with a changed `def`, `class` and
      `__all__`: each listed; an indented method is not, as the text says.
- [x] Not executed: other Python versions; the text says so and tells the reader to re-run a
      row on the project's interpreter.

## RED and GREEN (with the generic skill)

- [x] RED reviewer, small Python scenario (11 planted): opus 11 of 11, haiku 10 of 11 (missed
      the duplicated default). Large Python scenario (15 planted): opus and haiku 15 of 15 in 2
      of 2 runs each. The baseline does not fail for a reviewer.
- [x] RED implementer: haiku 2 of 2 runs add an unspecified minimum-sample gate; opus 0 of 2.
- [x] GREEN implementer (both skill texts): haiku 0 of 3, opus 0 of 1. GREEN reviewer, large
      scenario: opus 15 of 15, haiku 15 of 15 in 2 of 2 runs, with the pair table; the
      duplicated default is found by both tiers.
- [x] Diff against RED: nothing found in RED is missing in GREEN.

## REFACTOR

- [x] CLOSED: the examples' own rule read as the recommended rule (an arm compared the
      example's substring test with the word-boundary pattern in the code under review): the
      note "The examples show the SHAPE" now opens the section.
- [x] CLOSED: a case-insensitive pattern beside `casefold()`: a measured row added.
- [x] CLOSED: the order of the two results in the last table column is stated.
- [x] CLOSED: a sentence naming an older Python version read as history; replaced with what
      was and was not run.
- [x] DECLINED (covered by the shape note): the Python and Rust `cost_cents` examples round by
      different mechanisms.
- [x] DECLINED (not claimed): the argparse example for a change without a command line; the
      rule is "one default", the example is one instance.
- [x] DECLINED (probe artifact): "nothing measured" and "searches not run" in a text-only run.
- [x] Width and fence check: no line over 100 columns outside the front-matter description,
      tables and the fenced grep line; every fence closed; non-ASCII only in the two table rows
      whose input is the letter sharp s.

## Re-run on the final text

- [x] Implementer haiku and opus with both texts: no added condition; the reviewed
      word-boundary rule kept and the two readings raised as a question. Reviewer large
      scenario haiku 15 of 15.
- [x] Quote-back, opus and haiku, on the family's rules: every question answered with a direct
      quote, none NONE (counts in the generic checklist).
- [x] Tiers: opus and haiku on every probe.

## Other checks

- [x] Description: 601 characters, starts "Use when", names triggers and that the skill loads
      alongside `bitranox:coding-consistency`; parses to `['description', 'name']`.
- [x] Router replay on the regenerated trigger map: "my python code uses round() in one place
      and int() in another, is the duplicated logic consistent?" nominates this skill (the
      Rust companion ties on the shared words).
- [x] History-phrase finder and private-name grep over the skill directory: no hit.
- [x] Body 229 lines, no supporting files; four Python blocks of 4 to 44 lines, each part of
      one runnable module.
- [x] Trigger map and catalogue regenerated and in sync (90 skills).
- [x] Text test `hooks/tests/test_consistency_skill_family_text.py` covers this skill.
