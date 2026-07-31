# skill-writer checklist - interface shape + machine-drivable CLI

Two sections added to `process-review-enhance-code-quality`, each with its own RED.

## PLAN

- [x] Skill type: discipline (a review procedure that must be followed, not adapted away).
- [x] Test approach: application scenarios - give a baseline reviewer a project carrying the
      defect and see whether the procedure surfaces it.
- [x] Two fixtures, two languages, because the sections claim to be language-agnostic and
      testing only one language would leave that claim unverified.
- [x] Scope: edits to an existing SKILL.md, no new supporting files.

## RED - the first attempt FAILED to fail, and that is recorded on purpose

- [x] Fixture 1: `conveyor-monitor`, TypeScript, 199 lines, 13 pair-returns, one inverted.
- [x] Baselines run on sonnet AND haiku (a capable model can reason around a missing rule and
      mask the gap; a literal one shows it).
- [x] RESULT: both baselines FOUND the shape and the inversion. RED did not fail.
- [x] Diagnosed, not explained away. Two causes, both mine:
      1. The inverted function carried a docstring SAYING it was inverted. The fixture
         announced its own planted defect.
      2. At 199 lines in one directory the aggregate is visible in a single read, so no
         counting is needed. The real observation came from a 54-module package.
- [x] Fixture 2: `fleet-telemetry`, TypeScript, 23 modules, 372 lines, largest module 21 lines,
      26 pair-returns, one inverted with NO comment, a 4-name parameter group across 8
      collectors, three tramped parameters, receiver re-parses.
- [x] Fixture COMPILES (`tsc --noEmit` under strict + noUncheckedIndexedAccess exits 0), so the
      "green gate" premise the scenario states is true rather than asserted. An earlier
      generator bug emitted invalid identifiers; a fixture that does not build would have been
      reviewed as a compile error instead of as the shape question.
- [x] RED RESULT (the gap, confirmed): haiku missed the repeated shape ENTIRELY - no finding
      across 26 instances, where on the 199-line fixture it had raised it. sonnet found it and
      ranked it MINOR, tenth of eleven findings, and MISSED the inversion that haiku caught.
      Neither counted anything. So the defect is not blindness but local judgement of a global
      pattern, plus luck on the correctness bug.
- [x] Fixture 3: `spoolcheck`, Python + click, for the CLI gap. No structured mode, warnings on
      stdout, exit 0 on a failed inspection, an unhandled exception escaping as a traceback.
      All four verified present by RUNNING the tool before handing it over. Tests green.
- [x] RED RESULT: four reviews (2 models x 2 fixtures) produced zero findings about
      machine-readability. red3-sonnet ran the tool, measured coverage and installed the
      package - ten findings, none about `--json`, typed errors, stderr routing, or what an
      exit code means to a caller. It called the exit codes "inconsistent" without noticing a
      failure reported success.

## GREEN

- [x] Section "Interface shape - COUNT it, do not read for it": six counts with thresholds, five
      judgement rules, and the measured tell (43/568, three reviews missed it; then the fixture
      result above).
- [x] Section "A CLI must be drivable by a machine": five requirements as a table, the
      ran-vs-could-not-run distinction, and an explicit warning that the existing "CLI surface"
      row does NOT cover it (it audits the modes that exist).
- [x] Two checklist rows added, plus an instruction that these two are COUNTED and a sweep
      claiming no findings must state the numbers.
- [x] Both sections state their language-agnostic method (parser where available, grep where not).

## Quality

- [x] Added lines are ASCII only (74 lines, verified; the file's pre-existing box-drawing
      diagram is untouched).
- [x] No table hand-alignment introduced; no malformed rows.
- [x] No new supporting files, so no routing table changes and no bundled scripts to test.
- [x] Version bumped 5.111.0 -> 5.112.0 (MINOR: content change to an existing skill).

## Deferred

- [ ] GREEN re-run: replay fixture 2 and fixture 3 against the EDITED skill and confirm the
      shape census and the CLI rows now surface. Not yet done at the time of writing.
