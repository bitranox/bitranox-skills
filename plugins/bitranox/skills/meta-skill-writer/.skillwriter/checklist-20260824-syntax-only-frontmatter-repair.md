# skill-writer checklist - meta-skill-writer (one named exception to the Iron Law)

Change: the Iron Law gains a single carve-out, a SYNTAX-ONLY FRONT-MATTER REPAIR, defined by three
mechanical conditions rather than by judgement, plus a sentence naming how it relates to the
"No exceptions" list above it.

## PLAN

- [x] Skill type: discipline. The Iron Law is the rule that has to hold under "this one is small
      enough" pressure, so the test approach is a pressure scenario at both arms, plus a second
      scenario in the direction where the new exception must NOT apply.
- [x] Scenarios drafted before editing: (1) a colon-space repair with parser and byte-identical
      trigger evidence but no subagent run; (2) a description reworded to add a routing keyword,
      front matter valid throughout. The exception must permit (1) and refuse (2).
- [x] Scope: one section of an existing skill. No frontmatter change, no supporting files.

## RED

- [x] Baseline run on the pre-change text with scenario (1). Chose B, do not ship, quoting
      "Edit skill without testing? Same violation." The pre-change text forces the opposite of
      the intended rule, which is the failing test.
- [x] The baseline named the missing line itself rather than merely choosing wrong. Verbatim:
      "The text never defines what a pressure scenario is supposed to detect when the edit is
      proven to carry zero behavioral or routing difference (byte-identical trigger file). The RED
      step's own rationale ... presupposes there is new teaching content to test against; here
      there is none."
- [x] It also recorded the reasoning route, which is the shape a missing rule leaves behind:
      "I had to extend the rule to this case by analogy rather than by an explicit line covering
      it" and "I guessed that this case falls under ... 'documentation updates' rather than
      treating it as an unlisted, ungoverned category."

## GREEN

- [x] Post-change text run against both scenarios. Scenario (1) chose A, ship, quoting the new
      clause "is tested by a parser and the derived artifacts, not by a pressure scenario" and
      walking all three conditions against the stated evidence.
- [x] Scenario (2), the direction where the exception must NOT apply, chose B with the verdict
      unchanged, quoting "Rewording a description to say something DIFFERENT is never this
      exception, however small the edit looks - that changes what the router matches, which is
      behaviour." An exemption tested only where it fires is the failure this arm exists to
      prevent.
- [x] Both dispatches required a "Skill gaps" section, and both lists are recorded here rather
      than summarised away.
- [x] Diffed GREEN against RED in both directions. Nothing the baseline produced is missing: the
      baseline's reasoning about the Iron Law covering edits survives intact in scenario (2),
      where it is now the governing answer rather than an over-broad one.

## REFACTOR

- [x] Gap "the No exceptions list sits directly above One named exception and the text never
      states the relationship; I resolved it by inference, not by a quoted rule" - CLOSED. A
      sentence now names it: every item on that list is a judgement, the list forbids the
      judgement rather than the existence of a carve-out.
- [x] Gap "the text does not say what happens if the three conditions are true but never written
      down" - CLOSED. The clause now reads that conditions true but unwritten do not count,
      because the artifact is where the proof lives.
- [x] Gap "the router and the derived trigger artifact are not defined mechanically in-text" -
      DECLINED. Both are defined elsewhere in this skill and in the repo's CONTRIBUTING; naming
      a specific filename inside the Iron Law would bind a general rule to one repo's tooling.
- [x] Gap "neither scenario tested a partial-exception case" - DECLINED as already governed; the
      probe itself judged "that generalization is clear, so no gap there in practice", and
      "Fail any one of the three and the Iron Law applies unchanged" states it.

## Quality

- [x] ASCII only across the whole file, verified after editing. No em-dashes, no curly quotes.
- [x] No address, MAC, hostname or machine path added - verified over the file, zero hits.
- [x] Present tense, no session narrative, no record of how the section read before this change.
- [x] Frontmatter untouched; the description still states triggers only.
- [x] Hub skill, so the body legitimately runs long; the change adds one section to an existing
      one and no new supporting file.

## Deliverables

- [x] `SKILL.md` Iron Law section, applied.
- [x] The rule it sanctions is enforced mechanically, not left to prose: `harness_checks` gains
      `frontmatter_yaml_error()` and a shared `frontmatter_file_problems()`, and `repo-gate.py`
      gains `check_frontmatter` so a changed SKILL.md is gated on front matter a parser accepts.
- [x] Sibling tests in `hooks/tests/test_harness_checks.py` and `hooks/tests/test_repo_gate.py`,
      each watched to fail before the implementation.
- [x] Version bumped in `plugin.json`.
