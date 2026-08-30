# skill-writer checklist - compuse-toolbox (`guard_replay --sample` spread)

Change: `guard_replay --sample` draws its firings evenly across the corpus instead of filling from
the front, and the skill now states what a sample can and cannot establish. One new helper
(`_spread_sample`), two new tests, one table-row edit, one new rationale bullet, new `--help` text.
No frontmatter change.

## PLAN
- [x] Skill type: reference (a tool index with a per-tool rationale). The text change is one row
      and one bullet in an existing hub, not a new tool.
- [x] Trigger is measured, not hypothetical. `classify()` filled the sample with
      `if len(samples) < sample`, so it returned the first N firings in corpus-walk order; the walk
      is file by file, so those N are whichever project sorts first. Reading 40 of 557 firings that
      way put a residual at ~10 percent and that figure reached a published CHANGELOG; classifying
      all 557 put it at ~2 percent (3 of 187 and 8 of 360), because the 40 came almost entirely
      from one project that writes scripts through heredocs. The 517 unread firings also held four
      shapes the sample never contained - commands behind `nice`/`ionice`/`timeout` and after a
      `do` keyword - and those four were a live regression in the predicate being measured.
- [x] Scope: one helper, two tests, one table row, one rationale bullet, `--help`, CHANGELOG,
      MINOR version bump.
- [x] The spread is the DEFAULT, not an opt-in flag. A first-N sample is misleading for the
      documented purpose in every case, so an opt-in would keep shipping the trap to everyone who
      does not know to ask for the fix. It is a visible behaviour change - the same command returns
      different example firings - which is why the bump is MINOR and the CHANGELOG says so.

## RED - unit
- [x] The spread test fails against the pre-change implementation with the failure mode it names:
      `AssertionError: sample is still the first N`, `assert ['fire 000', 'fire 001', 'fire 002',
      'fire 003', 'fire 004'] != ['fire 000', ...]`. The two neighbouring sample tests pass against
      that same pre-change module, so the new assertion is what fails, not the fixture.
- [x] `test_a_sample_larger_than_the_firings_returns_them_all` passes on both implementations. It
      is recorded as a regression guard for the `n >= len(fires)` branch, NOT as a RED - a test
      that never failed proves nothing about the change.
- [x] The assertion is not satisfiable by a lucky draw: it requires 5 distinct firings, corpus
      order preserved, and the last pick at index >= 80 of 100. A front-filled sample fails the
      last two of those independently.

## RED - behavioural
- [x] Arm: an inert text-only probe agent on the least inferential model tier, given the
      pre-change table row and asked to write the release note for a narrowed matcher. The
      scenario uses different numbers from the worked example in the new text (900 firings,
      `--sample 30`, 6 misses, against the text's 40 of 557) so the arm has to apply the rule
      rather than recognise the example.
- [x] It published the extrapolation, which is the error the change closes:

      > "The narrowed matcher removes 900 false positives; sampling of 30 removed cases indicated
      > that approximately 20% (1 in 5) were legitimate detections the narrowed scope no longer
      > catches."

      and went on to compute "roughly 180 missed cases", having itself noted that 30 is 3.3% of
      900. Its `Skill gaps` names the ambiguity the change removes: it read "a percentage tells you
      volume and never whether the warnings are right" and concluded the percentage was still
      reportable.

## GREEN
- [x] Same tier, same scenario, post-change text. It refused, and quoted the governing line rather
      than paraphrasing it:

      > "when a proportion is the answer you need, classify every firing" ... "I would not publish
      > a release note with 'approximately 20%' or '~180 genuine misses' derived from this sample
      > alone."

- [x] Both arms were asked for a `Skill gaps` section and both answered; GREEN reported three
      gaps, decided below.
- [x] Both directions compared, on the recorded arm outputs - the quoted decisions and each arm's
      gaps list. The only item present in RED and absent from GREEN is the extrapolated percentage
      and the count derived from it, which is the output this change exists to remove. The sample
      fraction itself survives in GREEN, as the reason for the refusal rather than as the basis for
      a multiplication.
- [x] Re-derived on the live corpus rather than taken from the arms: replaying a shipped guard
      predicate with 29 firings, the new draw returns 8 samples from 7 distinct working
      directories; the pre-change draw returns 8 that all sit inside a single project tree.

## REFACTOR - every reported gap closed or declined
- [x] "No minimum sample size is stated." DECLINED. A threshold is an invitation to extrapolate
      above it, which is the failure being closed. What a sample can establish does not change with
      n: it shows shapes, and a ratio needs every firing classified. Stating a number would answer
      a question the rule does not turn on.
- [x] "A release note wants one confident figure; the rule refuses to extrapolate." DECLINED as a
      text change - the governing sentence already answers it: read the sample for what the firings
      look like, then classify the whole set when the answer is a ratio or a residual. That is an
      instruction to go and get the real number, not to hedge. Adding release-note-specific wording
      would narrow a general rule to one venue.
- [x] "Does the rule apply to release notes specifically or to any use of a proportion?" CLOSED by
      the existing wording, which names the ANSWER SHAPE and not the venue: "when the answer is a
      ratio or a residual". Any use of a proportion is in scope.
- [x] No gap needed a text change, so no re-test was owed: re-testing questions the fix did not
      touch costs a cycle and answers nothing.
- [x] The lesson also lives where the tool is used, not only where it is documented:
      `_spread_sample`'s docstring and `--help` both carry it, so a reader who never opens the
      skill still meets it.

## Quality
- [x] Frontmatter untouched. Description measured with `len()`: 1009 of 1024, unchanged by this
      edit, so no routing keyword moved and no trigger was displaced.
- [x] Stdlib only - the helper is arithmetic over a list, so the script still imports in a bare
      environment, which the contribution gate needs.
- [x] The sample stays in corpus order after being spread, so a reader compares firings in the
      order they occurred; only the selection changed, not the presentation.
- [x] No session narrative, no scratch or temp paths, no machine-specific addresses or hostnames
      in the skill, the script, or this artifact.
- [x] Tables reformatted and the tell sweep run clean on the changed Markdown.
- [x] Full gate green with CI's dependency set: `repo-gate.py --ci` reports all checks passed,
      4003 passed / 13 skipped / 1 xfailed. The xfail is the documented write-then-run gap and is
      STRICT - an XPASS means the gap closed and the marker goes, rather than being re-added.
