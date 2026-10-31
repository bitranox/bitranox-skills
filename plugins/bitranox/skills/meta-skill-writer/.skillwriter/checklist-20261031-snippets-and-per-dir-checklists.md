# Review checklist 2026-10-31: execute added snippets before GREEN; one checklist per skill dir

Change: a paragraph in "GREEN: Write Minimal Skill" (execute every command and snippet the edit
adds, against the real target or a fake, before the GREEN probe; a probe tests that text is
followed, never that it works), two sentences after the review-artifact paragraph (the gate checks
each skill directory on its own, and reports only after its test run), and two GREEN checklist
lines.

## Claims and their evidence

- [x] The checklist check is per skill directory: `skill_review_failures` in
      plugins/bitranox/hooks/repo-gate.py builds the `.skillwriter/` prefix per changed skill name
      and fails each name with no artifact under its own prefix (read, lines 1193-1204).
- [x] It reports only after the test run: the gate accumulates `failures` and runs pytest before
      returning them (repo-gate.py, the check list around line 2727, then `pytest_check`); read.
- [x] The wait-loop example: the 2026-10-31 compuse-ssh draft's check never saw `pgrep` report the
      process gone (pgrep exits 1 when nothing matches), a GREEN probe quoted it verbatim, a
      fake-ssh run caught it (contribution-queue entry, the session that shipped 10.9.7).
- [x] The change adds no executable command or snippet, so there was nothing to execute for it.

## Probes (text only, haiku, passage pasted, quote-back required)

- [x] RED (pre-edit passages): Q1 per-dir count only inferred ("This is an inference"), Q2 "must
      you execute the snippet first" NOT COVERED, Q3 "does a verbatim quote show it works" NOT
      COVERED.
- [x] GREEN (edited passages): 4 of 4 answered by quote - two checklists, one per skill dir; yes,
      execute first, with the reason; "A probe tests whether the text is FOLLOWED, never whether
      what it says WORKS"; a fake standing in for the target.
- [x] GREEN's one actionable gap, how to learn early that a checklist is missing, closed with the
      "reports that only after its test run" sentence and the list-before-committing step.

## Gaps declined

- Checklist format and contents: the section's own Good/Bad example covers it.
- Non-marketplace repos: the existing "may additionally require" sentence already scopes it.
- How to build a faithful fake: per target, out of this skill's scope; the two examples suffice.
- Whether two per-skill checklists may share one probe run: "each recording its own probe" is the
  rule, and a shared run would be recorded in each.
- [x] Final probe on the final text: 3 of 3 answered by quote (two checklists, one per skill dir;
      reported only after the test run, so list the touched dirs before committing; execute
      first, because a probe tests that text is followed, not that it works).
- [x] Its gap "how to identify the twin of a mirrored skill" exposed a wrong example: a mirrored
      twin lives in another repo, which this gate never reads (`skill_review_failures` sees only
      paths changed in its own repo). The parenthetical was cut to "one sentence added to two of
      them", the case that was measured (meta-dream-tree and meta-dream-crosstree, 2026-10-31).
- [x] Its other two gaps (CONTRIBUTING not shown, checklist format) are passage truncation: the
      full section and its Good/Bad example cover them.
