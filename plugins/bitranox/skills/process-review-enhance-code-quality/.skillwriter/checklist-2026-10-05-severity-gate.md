# skill-writer checklist - process-review-enhance-code-quality (severity-gated loop exit)

Change: the sweep loop no longer ends on a sweep that finds nothing and changes nothing. It ends
when a full checklist walk finds no SEVERE and no MEDIUM finding a realistic caller can reach. A
finding only an exotic path reaches (a crafted input outside the documented use, a microsecond
race, a platform path alias) is fixed when cheap, otherwise recorded under `# Code Quality` with
its reach as the reason. Each sweep reports a per-severity table so the plateau is visible.
Updated every statement of the old rule: the Workflow diagram, "The outer loop is the point",
Step 7, the aspect-checklist report line and the Common Mistakes rows. Shipped in plugin 7.42.0.

## PLAN

- [x] Skill type: discipline (a loop with an exit rule). Test approach: decision scenario at the
      exit point, two variants so the gate is shown to bite in both directions.
- [x] Motivation, measured on one library: ten sweeps; no SEVERE after sweep 7; MEDIUM per sweep
      8, 6, 6, 7, 7, 7, 4, 2, 7, 4; three of sweep 10's four MEDIUM-or-higher findings caused by
      sweep 9's own fixes; the late findings were a 17,000-emoji Windows path, a loopback UNC share
      alias and a microsecond swap race; about a million reviewer tokens per sweep. The owner
      judged the continued sweeping over-engineering and chose a severity-gated stop.
- [x] Kept the two existing reasons for sweep 2+ ("a fix creates findings", "one sweep does not
      see everything") and added that, in an adversarial open-charter review, neither runs out.

## RED

- [x] Contamination check: `redcheck --corpus-cascade` over the library repo where the rule was
      first written down reports INHERITED COVERAGE (its CLAUDE.md states the new rule), so the
      arms run from a neutral directory outside that tree, where the cascade assembles 0 documents,
      with all tools disabled and skills disabled, the skill text pasted into the prompt.
- [x] Scenario: a reviewer holding the skill has finished sweep 10 of a fictional archive-extractor
      library, with the per-sweep severity table above and four MEDIUM findings. Variant A: all four
      reachable only by exotic paths (a 17,000-emoji `dest` on Windows, a loopback UNC alias of a
      blocked directory, a microsecond symlink-swap race, a `PathLike` whose `__fspath__` changes
      per call). Variant B: the fourth replaced by a realistic one (the README-documented
      `max_size = "500MB"` in the config file silently disables the size bound).
- [x] RED, current text, `sonnet`, variants A and B (run twice each) and `haiku` variant A: every
      run chose sweep 11, quoting "Stop only when a full sweep ... produces no findings and no
      changes". Sonnet regraded the UNC alias and the race to SEVERE as "security issues" and
      forecast "one to three more sweeps"; every run's gaps named the missing exit: "No stopping
      rule beyond zero", "Cost is not a stop condition anywhere in the skill".

## GREEN

- [x] `sonnet` A: ends the loop, quoting "A finding only an exotic path can reach does not hold the
      loop open, at any severity"; keeps all four at MEDIUM ("reach is not a regrade"); proposes the
      cheap fixes and recommends acceptance with the reach recorded for the rest; still presents
      and settles every finding before the re-score.
- [x] `sonnet` B: runs sweep 11 because the config-file finding is "squarely a realistic caller",
      quoting "do not stop while one MEDIUM a realistic caller reaches is still open"; treats the
      other three as exotic with the same dispositions as A.
- [x] `haiku` A and B: same decisions as sonnet in both variants.
- [x] Diffed against RED in both directions: the RED runs' root-cause fix proposals (canonicalise
      before the blocked-directory check, open with no-follow instead of check-then-open, census
      the other config keys the refactor touched) all reappear in GREEN. Nothing lost.

## REFACTOR

- [x] Skill gaps from every RED and GREEN run recorded. Closed in the text:
      "cheap" undefined -> "a local change plus its test, no new mechanism";
      a documented CLI argument fed a crafted value read as realistic -> "Judge the VALUE as well as
      the entry point";
      no format for presenting an exotic finding -> "in the Step 5 format with the suggested fix
      `accept: reachable only by ...`";
      "the last sweep" ambiguous against the gate, and MINOR handling in it -> "the one that met the
      gate - still presents and settles all its findings, MINOR included".
- [x] Declined, with reasons: no token budget or sweep cap (the gate is the cost control; an owner
      stopping the loop is user authority, not a skill rule); fix-caused versus pre-existing exotic
      findings (the text already says "at any severity" and reach decides); reach column missing
      for earlier sweeps (a scenario artifact); scoping later sweeps to changed code (out of scope
      for this change); model-tier dispatch impossible without tools (a property of the test rig).
- [x] Added, from RED behaviour: reach and severity are separate axes, so regrading a finding
      cannot move it across the gate (a new Common Mistakes row).
- [x] Added for untrusted-input projects: where taking hostile data is the documented job (a parser,
      an extractor, a server), that data is a realistic caller, so the gate cannot be read as
      licence to accept the defect class such a project exists to prevent.
- [x] Quote-back, `haiku`, final text, five contested questions: every answer a verbatim quote of
      the governing sentence, none NONE.

## Quality

- [x] Every statement of the old exit rule replaced; grep for "finds nothing", "changes nothing",
      "clean sweep" and "zero findings" leaves only the sentences that reject the old rule.
- [x] Tables canonical per `reformat_tables --check`. ASCII only, present tense, no session
      narrative, no private hosts or paths, no real project names. Measured figures generalised to
      "one library".
- [x] Frontmatter and description unchanged, so `skill_triggers.json` needs no rebuild.
- [x] Security scan: prose and tables only, no secrets, credentials or infrastructure references.

## Deliverables

- [x] `SKILL.md` edits as listed above; no script, so no `tests/` change. Version 7.42.0 (MINOR: a
      changed loop exit with a new reporting table), `pyproject.toml` matched, CHANGELOG entry.
