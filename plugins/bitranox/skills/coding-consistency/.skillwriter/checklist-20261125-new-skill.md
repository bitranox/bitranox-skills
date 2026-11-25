# skill-writer checklist - coding-consistency (2026-11-25, new skill)

A new language-neutral skill for the consistency lens of a change: seven pairings (sibling paths,
halves of one figure, figures and rules that go together, a literal and what it stands for, code
and the spec's fixed points, code and its own prose, an interface and its contract), four axes a
pair is compared on (set, rule, window, unit), seven rules for whoever writes the change, and a
review procedure that returns a pair table with a verdict per row. It routes Python to
`bitranox:coding-python-consistency` and Rust to `bitranox:coding-rust-consistency`. No scripts.

Decisions: d-20261125-fd4283d3, d-20261125-408ba02e, d-20261125-4304732c, d-20261125-b09527cd, d-20261125-f22e8da0

- [x] Receipt fresh (armed for the session, skill-writer loaded in this agent). Step 0b before
      the first edit: `skill_decisions.py show coding-consistency` reports no skill, the skill
      did not exist. After the ledger was written, `skill_decisions.py check coding-consistency`
      reports 0 findings.
- [x] Not mirrored: the family is new and ships only from this marketplace.
- [x] Name check: no skill named `coding-consistency`, `coding-python-consistency` or
      `coding-rust-consistency` existed; the working names are kept.
- [x] Existing coverage searched over the whole skills tree with `bash -c 'grep -rniE ...'`
      (gitignored files included). Three shipped skills touch the subject and none covers the
      lens: `process-agents-subagent-driven-development` reviews a change against its plan ("A
      departure recorded nowhere is also a DEFECT"), `process-plan-writing-plans` has a "Type
      consistency" self-check of a plan, `process-test-design` has a rule for a consistency
      test. The skill's scope line and its See-also entries keep it apart from them.
- [x] Skill type: technique (pairings, writing rules, a review procedure); test is application.
      Scenarios, each a planted service with a written spec, each prompt ending with a request
      for a "Skill gaps" section:
      - small Go change (9 planted defects), small Python (11), small Rust (11): reviewer, told
        the lens name only;
      - large Python change, 13 files, about 20 KB, 15 planted defects: reviewer;
      - implementer: four tasks adding an alert and a cost column beside existing figures, with
        a product-owner note that an earlier prototype's alert flapped.
- [x] Probe set-up: headless `claude -p --output-format stream-json`, opus and haiku, every
      file, shell, web, Agent and Skill tool disallowed, a fresh empty working directory per
      run; the answer is the FIRST assistant text block. GREEN arms carry the SKILL.md texts in
      the prompt, marked as the text under test. The skills are installed nowhere, so no arm
      could load another copy.
- [x] Inherited-coverage check: `redcheck.py --corpus-cascade` for the probes' working
      directory reports nothing that states the lesson.

## RED (no skill)

- [x] Reviewer, small scenarios: Go opus 9 of 9, haiku 9 of 9; Python opus 11 of 11, haiku 10
      of 11 (missed a command-line default of 100 beside a function default of 200); Rust opus
      11 of 11, haiku 11 of 11.
- [x] Reviewer, large scenario: opus 15 of 15 in 2 of 2 runs, haiku 15 of 15 in 2 of 2 runs.
- [x] Implementer: opus 2 of 2 runs clean (shared rule, shared window, one cost function, the
      listed signature kept, no added condition, the flapping raised as a question). Haiku 2 of
      2 runs added a minimum-sample gate the spec does not have (`ALERT_MIN_TICKETS = 20`,
      `MIN_ALERT_TICKETS = 20`) and recorded it only in its own notes: "Design 5.1 is silent on
      a minimum sample ... I chose 20", "Set ALERT_MIN_TICKETS = 1 to restore the literal
      rule".
- [x] RED verdict: the baseline does NOT fail for a reviewer on either tier at these sizes.
      It fails for the haiku implementer on one behaviour, an unspecified suppressing
      condition added under a stakeholder's wish. The skill's description and text claim no
      gain in reviewer detection (ledger d-20261125-f22e8da0).

## GREEN (generic skill, plus the language skill where one exists)

- [x] Implementer: haiku 0 of 3 runs with the gate, opus 0 of 1; every run ships the specified
      rule and puts the minimum sample to the owner as a question. Flip on haiku: 2 of 2 to 0
      of 3.
- [x] Reviewer: large scenario opus 15 of 15, haiku 15 of 15 in 2 of 2 runs; Rust opus 11 of
      11, haiku 11 of 11 in 2 of 2 runs; Go opus 9 of 9, haiku 9 of 9. Every arm returns the
      pair table with AGREE, DISAGREE, ONE-SIDED and ADDED verdicts.
- [x] Diff against RED, both directions. Gained: the pair table; findings with a concrete
      input on which the two sides differ (large scenario: haiku 1 before, 10 after; opus 0
      before, 4 after); no added condition from the haiku implementer. Lost: nothing, no
      planted defect found in RED is missing in GREEN.

## REFACTOR

- [x] CLOSED: a spec that sets two things apart on purpose (each side compared with its own
      spec point; an unexplained gap goes to the suspicions as a question).
- [x] CLOSED: a named constant that stands in for a per-item value is still pairing 4.
- [x] CLOSED: a project with no record of accepted departures ("the question in your hand-over
      is all there is, and the condition stays out").
- [x] CLOSED: what a second path does where the spec is silent, and that the choice is listed
      in the hand-over.
- [x] CLOSED: review sources numbered 1 to 7, source N feeding pairing N, so the language
      skills can cite them.
- [x] CLOSED: all four comparison cells filled in every row, `-` for an axis the pair lacks.
- [x] CLOSED: "the spec reads both ways" as a third answer beside a quoted line and "silent".
- [x] CLOSED: an `ADDED` row is a finding although only one side exists, and is rated by what
      it holds back.
- [x] CLOSED: prose claims that restate one code row share that row's finding.
- [x] CLOSED: the rating scale (the higher level when two fit; a spec-named outside caller is a
      caller that breaks; a low interface finding says outside callers were not checked).
- [x] DECLINED (judgement left to the spec's owner): whether a rounding step in a rule versus
      its display is a finding or only a question when the spec leaves the unit open.
- [x] DECLINED (covered): a rating for `ONE-SIDED` rows; the scale's levels are by what is
      seen and apply to every verdict.
- [x] DECLINED (covered): a record of departures exists but has no entry; "the condition goes
      in only together with its entry there".
- [x] DECLINED (judgement): definitions of "ordinary use" and "can occur"; who the spec's owner
      is (project-specific); how to word the answer to the requester.
- [x] DECLINED (owned by the caller): a requested output format that differs from the table;
      the table is returned in addition.
- [x] DECLINED (not claimed): an author returning a pair table; the table is review output.
- [x] DECLINED (covered by pairing 4's wording "while the real value is configured or differs
      per instance"): fixed unit factors such as `/ 60` are not held values.
- [x] DECLINED (out of scope): defects outside any pair; the scope line sends them to other
      reviews.
- [x] DECLINED (covered): moving an already reviewed rule to a shared home when the plan's
      scope names later tasks only; rule 1 says the rule moves, and the arm that asked did so
      and listed it.
- [x] DECLINED (probe artifact): "could not run the searches" in a text-only run.
- [x] DECLINED (covered): a reported conflict between "a single side on an open point is not a
      finding" and "two sides that disagree are a finding"; the first is about one side, the
      second about two, and the arm applied them that way.
- [x] Width and fence check: no line over 100 columns outside the front-matter description,
      the tables and the fenced row format; every fence closed; ASCII only.

## Re-run on the final text

- [x] Implementer haiku and opus: no added condition, owner question raised. Reviewer large
      scenario haiku 15 of 15, Rust haiku 11 of 11, both with the pair table.
- [x] Quote-back, opus and haiku, 13 questions on the rules of the family and 5 on the last
      edits (an added cooldown with a silent spec, a spec-named outside caller, the
      not-checked sentence, an unexplained gap between two spec points, the second path on a
      missing field): 36 of 36 answered with a direct quote of the governing line, none NONE.
- [x] Tiers: opus and haiku on every probe.
- [x] Not measured: the effect on a change of real plan size, and the implementer effect on
      opus (its baseline was already clean).

## Other checks

- [x] Description: 683 characters (`len()` of the parsed field), starts "Use when", names
      triggers only and the two routes; the front matter parses with a YAML loader to
      `['description', 'name']`.
- [x] Router replay with `skill-router.py`'s `match()` on the regenerated trigger map: "review
      this change for consistency: two code paths compute the same value differently" nominates
      this skill first; a Rust cast-and-duration prompt nominates the Rust companion first and
      this skill second; "my python function takes a dict parameter, make it a pydantic model"
      and "set up criterion benchmarks for my rust parser" nominate neither. A prompt that
      names only a stale docstring does not nominate the family.
- [x] History-phrase finder and private-name grep over the skill directory: no hit; no
      address, home or temp path.
- [x] Body 188 lines, no supporting files, one fenced row format and one summary block.
- [x] Trigger map and catalogue regenerated (`build_skill_triggers.py --check`: "in sync (90
      skills)"; `build_skill_docs.py --check`: "docs/skills.md in sync"); README and
      docs/installation.md counts set to 90.
- [x] Text test `hooks/tests/test_consistency_skill_family_text.py`: front matter, resolving
      `bitranox:` references, routing both ways in body and description, and that a companion
      cites only source numbers the generic pairing table has.
