# skill-writer checklist - coding-failure-modes (2026-11-26, new skill)

A new language-neutral skill for the failure modes of a required behaviour: ten numbered axes
on which a working environment varies (quantity, samples behind a rule, order and repetition,
timing and in-progress input, concurrency, interruption and leftovers, first run and long
absence, representation of one thing, locale and convention, platform and configuration), four
verdicts a variant can get (HANDLED, REFUSED, ASSUMED, NONE), rules that turn a silent outcome
into a visible one, and a review procedure that builds its own variant table from the spec
before reading the author's. No scripts, no language companions.

Decisions: d-20261126-d976e7db, d-20261126-caa66970, d-20261126-2b3d0edc, d-20261126-618a04ca, d-20261126-7fa73843, d-20261126-a7a4f7d6, d-20261126-779f0053, d-20261126-c8698399, d-20261126-102b70bf

- [x] Receipt fresh, skill-writer loaded in this agent. Step 0b before the first edit:
      `skill_decisions.py show coding-failure-modes` reports no skill, the skill did not
      exist. After the ledger was written, `skill_decisions.py check coding-failure-modes`
      reports 0 findings.
- [x] Not mirrored: the skill ships only from this marketplace.
- [x] Name check: no skill named `coding-failure-modes` existed; `coding` is a registered
      category.
- [x] Existing coverage read before writing. `process-test-design` has the input battery for
      a boundary (text, bytes, type, numbers, size, structure) and one parenthesis that says
      "enumerate every variant/caller a path serves" without a procedure;
      `coding-resilience` covers a dependency that is absent, slow or flaky;
      `coding-input-sanitization` covers validation and escaping at a boundary;
      `coding-consistency` covers two places that must agree, and its rule 5 a condition the
      spec does not carry; `process-review-requesting-code-review` and
      `process-review-enhance-code-quality` (invariants enforced by a test) have no list of
      environment axes. None has an author-side step that lists how the environment varies
      for a required behaviour and decides each variant, or a rule about a silent outcome.
      The scope line and the See-also entries hand the neighbouring subjects to those skills.
- [x] Skill type: technique (an enumeration procedure and a review procedure); test is
      application. Two implementer tasks and one review task, each a planted specification
      from a domain of its own, with the variation axes not named in the specification:
      - importer: a scheduled job that imports delimited files from an inbox directory
        exactly once, rejects a file with more than 10% invalid rows and moves it. Axes fixed
        before the first run: upload still in progress, overlapping runs, a crash between
        write and move, a name already present in the target, the extension in another case,
        decimal sign and encoding, zero data rows, a missing target directory, an unchecked
        header.
      - stall check: "below 5 units per minute for the last 3 minutes" from readings about
        every 10 s, an `ACK <line name>` command, and a per-shift summary. Axes fixed before
        the first run: few or no readings in the window, readings out of order or from a
        leading clock, the name in another case, spacing or Unicode form, a name that
        matches nothing, a shift over midnight, an alert across a shift boundary, a daylight
        saving day, a shift still running.
      - review: a short implementation of the importer that serves only the normal case.
- [x] Probe set-up: headless `claude -p --safe-mode --tools "" --output-format stream-json`,
      opus and haiku, a fresh empty working directory per run; the answer is the assistant
      text of the run. The skill is installed nowhere, and with every tool off no arm can load
      a skill. GREEN arms carry the SKILL.md text in the prompt, marked as the text under
      test, and end with a request for a "Skill gaps" section. The RED arms were not asked for
      that section; they had no skill text to report on.
- [x] Inherited-coverage check: `redcheck.py --corpus-cascade` for the probes' working
      directory assembles 0 documents, and `--safe-mode` loads no CLAUDE.md, so no arm
      inherits a text that states the lesson.

## RED (no skill)

- [x] Importer, implementer. Opus 2 of 2 runs: every fixed axis handled in code or stated in
      the hand-over, except a missing target directory in 1 run. Haiku run 1: every axis
      handled or stated, the upper-case extension stated as "ignored" with nothing reported
      at run time. Haiku run 2: an upload in progress and overlapping runs appear nowhere,
      and the upper-case extension is not mentioned.
- [x] Stall check, implementer. Opus 2 of 2 runs: a reading at or before the window start
      plus a maximum gap of 30 s; the name folded for case, spacing and Unicode form; the
      silent counter named as a gap ("no alert is raised"). Haiku 2 of 2 runs: the window
      counts as covered when its first and last reading lie within 30 s of the ends, so two
      low readings 170 s apart report a stall; the line name is compared in exact case with
      inner spacing kept, and run 1's hand-over says "`ack filler 2` works" while its code
      returns None for it.
- [x] Review. Opus found every fixed axis of the importer. Haiku found every one except
      overlapping runs.
- [x] RED verdict: the baseline does NOT fail for an opus implementer or for a reviewer of
      either tier at this size. It fails for the haiku implementer: whole axes absent in 1 of
      2 importer runs, the sample-count axis missed in 2 of 2 stall-check runs, an untraced
      claim in 1 run. The description and the text claim no gain for opus or for reviewers
      (ledger d-20261126-779f0053).

## GREEN (skill text in the prompt)

- [x] First draft, one run per cell. Importer: haiku and opus both carry a row for every
      fixed axis and report unmatched inbox entries by name. Stall check: haiku decides a
      minimum count of 12 readings and a maximum gap of 30 s, traces `ack filler 2` and the
      two-readings case, folds the name for case, spacing and Unicode form. Review: both
      tiers return their own table with findings; haiku now reports overlapping runs.
- [x] Diff against RED, both directions. Gained: the variant table in every implementer run
      (haiku 6, opus 4 over all rounds); the two axes the haiku importer run lacked; the
      sample count and gap on haiku; a report of unmatched entries. Lost or worsened in the
      first draft: the haiku stall check raised a new exception class through the function
      specified to return a bool, and raised from the acknowledge path and from the summary
      of a shift not yet started, where the RED runs returned a value; the opus stall check
      added five public functions beside the three specified. Cost: the answers grew from
      about 7 000 to 14 000-23 000 characters on haiku and from about 12 000 to 28 000-33 000
      on opus, with 32 to 69 table rows.

## REFACTOR

- [x] CLOSED: a check that cannot tell under a fixed signature (least-claiming answer, a
      warning on a change of state, the first open question; no new exception, no companion
      function).
- [x] CLOSED: "Refused is not crashed" (a refusal ends one item, the others go on).
- [x] CLOSED: when to refuse to start and when to warn.
- [x] CLOSED: what to name while no file exists (the function) and no test is written (input
      and expected result).
- [x] CLOSED: a variant served through an added condition (HANDLED, marked with the
      departure), a variant served in part (two rows), state a caller keeps (ASSUMED, naming
      the caller), "nothing" as the answer to what the user sees (the row leads the open
      questions), a role or task where no person is known.
- [x] CLOSED: the normal case gets no row; a boundary of one quantity is a test input.
- [x] CLOSED: the three parts of a stated departure are in the text itself, beside the
      pointer to `bitranox:coding-consistency`.
- [x] CLOSED: axis 2 reads "a span or a share" in the table and in the paragraph; three arms
      had reported the two as disagreeing.
- [x] CLOSED: a value that cannot be derived from what the source states is a guess and is
      labelled as one.
- [x] CLOSED: how often the warning is logged in a job that keeps no state (once per run).
- [x] CLOSED: the row "returning False is safe" contradicted "return the answer that claims
      least"; it now says False goes out only with the warning and the open question.
- [x] CLOSED: the pointer to `bitranox:coding-consistency` names its rule 5 (the reviewer judges
      an added condition on its merit) and its rule 7 (a changed signature is a breaking
      interface change, admitted only as a departure); checked against that skill's text.
- [x] CLOSED, review side: what to write in place of a verdict, a missing author table, rows
      with one cause sharing a finding, how an uncaught exception is rated.
- [x] DECLINED (judgement, depends on the predicate): which of two boolean values claims
      least.
- [x] DECLINED (out of scope, a design question): the remedy for a crash across two
      resources when the fix needs a schema another task owns.
- [x] DECLINED (owned by `bitranox:coding-input-sanitization` and the language): which
      Unicode normalisation or case folding to use, how to subtract aware datetimes across a
      daylight saving change.
- [x] DECLINED (judgement left to the author): how far to serve the forms a source emits
      before it becomes scope the spec does not carry; the text gives both routes (serve as a
      stated departure, or report as unmatched).
- [x] DECLINED (not an environment variant): two readings of an ambiguous spec sentence;
      they go to the spec's owner as a question under `bitranox:coding-consistency`.
- [x] DECLINED (judgement): how a pure function holds the "said once" state, whether a
      programming error such as a naive timestamp may raise, whether anybody reads a log.
- [x] DECLINED (covered by "Group the `NONE` rows per behaviour on one line"): a shorter
      table format. The length of the table is a known cost, recorded above.
- [x] DECLINED (probe artifact): "could not run a trace" in a run with no tools; the text
      says to state that the trace was read, not run.
- [x] Width and fence check over the file: no line over 100 columns outside the front-matter
      description and the tables, every fence closed, no odd backtick count, ASCII only.

## Re-run on the final text

- [x] Second round on the refactored text, one run per cell. Stall check: haiku and opus
      return False with a warning and an open question for a window that cannot carry a
      verdict, define no new exception class and no public function beside the three
      specified; both keep a minimum count and a maximum gap. Importer: both tiers carry a
      row for every fixed axis.
- [x] Third round, haiku, both implementer tasks, after the last wording fixes: the same
      results; the importer run leaves the upload in progress as an ASSUMED row with a named
      confirmer where the second round skipped recent files by age.
- [x] Quote-back, opus and haiku: 12 questions on the refactored text, 4 on the last wording
      fixes and 1 on the reworded "returning False" row. Every answer is a direct quote of the
      governing line, none NONE; a checker finds each quote in the text, and finds the quotes
      of the lines added in REFACTOR absent from the first draft.
- [x] Tiers: opus and haiku on every probe except the third round (haiku only).
- [x] Not measured: the effect on a change of real plan size; the reviewer rule "own table
      first" against a review that starts from the author's table; routing in a live session
      (the skill is installed nowhere yet).

## Other checks

- [x] Description: 779 characters (`len()` of the parsed field), starts "Use when", names
      triggers only; the front matter parses with a YAML loader to `['description', 'name']`.
- [x] Router replay with `skill-router.py`'s `match()` on the regenerated trigger map: "which
      failure modes and edge cases does this required behaviour have that could fail
      silently" nominates this skill alone; "review this change: which environment variants
      did the author miss" nominates it first and `coding-consistency` second; "write tests
      for the edge cases of this parser" nominates it beside `process-test-design`;
      "implement the login feature for our users", a dict-to-model prompt and a retry prompt
      do not nominate it.
- [x] Text tests: `hooks/tests/test_failure_modes_skill_text.py`, 13 tests. Run against the
      first draft 4 fail; with the row of axis 7 deleted and "There is no fifth" reworded 2
      fail; on the final text 13 pass.
- [x] History-phrase finder and the address and path grep over the skill directory: no hit.
- [x] No examples from the change whose review led to the skill (ledger d-20261126-102b70bf).
- [x] Body 183 lines, no supporting files, one fenced row format and one summary block.
- [x] Trigger map and catalogue regenerated for 91 skills; the skill counts in README and
      docs/installation.md raised to 91.
- [x] Security review of the diff: text only, no script, no address, host, credential or
      private path.
