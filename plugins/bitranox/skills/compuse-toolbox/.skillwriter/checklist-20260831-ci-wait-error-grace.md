# skill-writer checklist - compuse-toolbox (`ci_wait` tolerates a failing `gh`)

Change: `ci_wait` retries a failed fetch on its own duration budget (`--error-grace`, default 120s)
instead of ending the wait on the first one, and reports a missing `gh` rather than raising a
traceback. One table row edited, one rationale sentence added to the module docstring and `--help`,
two new exception classes, thirteen new tests. No frontmatter change.

## PLAN
- [x] Skill type: reference (a tool index with a per-tool rationale). The text change is one row in
      an existing hub, describing behaviour that changed underneath it.
- [x] Trigger is measured, not hypothetical. `gh run list` answered HTTP 502 intermittently while
      api.github.com was otherwise healthy; `GhFailed` was raised inside the poll loop but caught
      OUTSIDE it, so the first bad response ended the wait with exit 2, three times running, each
      time with twenty minutes still on the deadline.
- [x] Scope: the retry budget, the `GhFailed`/`GhUnavailable` split, the timeout report, one table
      row, `--help`, CHANGELOG, MINOR version bump. The bump is MINOR rather than PATCH because a
      flag is added to the published surface and the tool's observable behaviour on a failing fetch
      changes.
- [x] The budget is a DURATION, matching `--appear-grace`, so `--interval 5` cannot silently cut a
      120-second tolerance to 20 seconds. Expressed as a poll count it would move with `--interval`,
      which is the defect `--appear-grace` already carries a regression test for.
- [x] The streak resets on any answered poll. The measured fault was INTERMITTENT, and a cumulative
      count would end the wait on the fourth scattered 502 of a healthy twenty-minute run.

## RED - unit
- [x] All thirteen tests fail against the pre-change module, each with the failure mode it names:
      five `TypeError: wait_for() got an unexpected keyword argument 'error_grace_s'`, three
      `AttributeError: module 'ci_wait' has no attribute 'GhUnavailable'`, one uncaught
      `ci_wait.GhFailed: gh exited 1: HTTP 502 (api.github.com)` escaping the loop, one
      `assert 4 == 3` for the extra fetch the timeout report used to make, one
      `SystemExit: 2 - unrecognized arguments: --error-grace`, one `'Namespace' object has no
      attribute 'error_grace'`, and the end-to-end arm as
      `assert 2 == 0, a single 502 must not end a wait that had its whole deadline left`.
- [x] The end-to-end failure IS the reported defect: `main` returning 2 where the runs were green
      and only the first fetch failed.
- [x] The intermittent test discriminates consecutive from cumulative counting. With a budget of two
      polls it alternates failure and progress, so the consecutive streak never exceeds one while a
      cumulative count reaches the budget on the second failure and returns `error`.
- [x] The sustained-outage test asserts the CALL COUNT, not only the state: it must stop at the
      budget (3 polls of 30s inside a 90s grace), never at the 100-poll deadline. State alone would
      pass on a tool that spun for the full deadline and then reported the same thing.

## RED - behavioural
- [x] Arms: an inert text-only probe on the least inferential tier, given the table row and asked
      what to run and what to build around it, for a release step under a morning of intermittent
      502s. The tool is renamed in both prompts so neither arm can answer from the installed copy of
      this skill or from a memory entry that names the real one.
- [x] `redcheck --corpus-cascade` reports INHERITED COVERAGE over 947 documents. Adjudicated as a
      FALSE POSITIVE by the documented test: the shared terms are function words (action, around,
      comes, concrete, conditions, fired, guess, reply, turn, unless), not subject vocabulary.
      Confirmed by grepping the cascade for the real lesson keywords - no CLAUDE.md on the chain
      mentions `502` or `error-grace` in this sense, and the memory entries that name the tool are
      about deriving a sha and identifying the right run, not about tolerating a failed fetch.
- [x] **The behavioural RED did not flip on the ACTION, and that is the reportable outcome.** Both
      arms chose the same command and both said they would build nothing around it. Escalating the
      scenario until something failed would have manufactured a result.
- [x] It flipped on the REASON, and the RED reason is FALSE of the pre-change tool:

      > "Transient 502s are absorbed by the tool's polling loop. The tool retries every 30 seconds
      > (default `--interval`) ... A single 502 on one `gh run list` invocation just means the next
      > poll 30 seconds later tries again. Occasional transients do not accumulate or block."

      On that text's tool, one 502 ended the wait. So the arm reached the right action through a
      belief the code did not honour, which is the shape of the defect: a reader assumes a polling
      waiter survives a failed poll, and acts on that assumption without checking.

## GREEN
- [x] Same tier, same scenario, post-change row. Same action, and now a true reason, quoted rather
      than paraphrased:

      > "The tool's `error-grace` mechanism (default 120 seconds) is explicitly designed for exactly
      > this scenario ... treating HTTP 502 as 'weather' not a verdict ... Distinguish between
      > transient errors (which it waits through) and sustained outages (which it reports as
      > `error`)."

- [x] GREEN also derives the bound the row states, unprompted: that a burst exceeding the grace ends
      the step at exit 2, and that this is the right failure direction for a release gate.
- [x] Both arms were asked for a `Skill gaps` section and both answered; decided below.
- [x] Both directions compared on the recorded outputs. One candidate loss: run 1 of GREEN read exit
      2 as "the API became unavailable", narrower than the baseline's "timeout waiting for runs, a
      timeout polling, or persistent gh failures". Re-run of the same arm, everything else fixed:
      exit 2 came back as "couldn't determine the outcome". The narrowing does not reproduce, so it
      is run variation and not an edit-caused loss - recorded rather than restructured around.
- [x] Nothing else present in RED is absent from GREEN. The baseline's remaining items are scenario
      clarifications, not results about the tool.

## REFACTOR - every reported gap closed or declined
- [x] "If the 502 bursts routinely exceed 120 seconds, a retry loop on exit 2 would make sense."
      CLOSED by the tunable budget, discoverable at `--help` rather than enumerated in the row -
      a tool index states the guarantee and its bound, and `--help` is the current flag list.
- [x] "The issue could be a rate limit rather than a 502, and then the analysis changes." DECLINED
      as a text change, and it is the design decision itself: nothing classifies gh's message. A
      rate limit is retried exactly like a 502, costing four requests across the budget before the
      real error is reported with gh's own words. Reading the message for words meaning "transient"
      would be a guess about a remote system, and the first wrong guess restores this defect.
- [x] "Should the pipeline retry, alert, or stop on exit 2?" DECLINED - pipeline design, outside a
      tool index. The row states what each verdict means; what a release step does with it is the
      caller's.
- [x] "Trusting that the tool honours 'every workflow that fired'." DECLINED as a text change: the
      row already states the guarantee and `verdict()` holds it under test, including the case of a
      completed run with a null conclusion.
- [x] Repository context and workflow environment: scenario artifacts, not gaps in the text.
- [x] No gap needed a text change, so no re-test was owed on the fixes.
- [x] The lesson lives where the tool is used, not only where it is documented: the reasoning is in
      `wait_for`'s docstring, in the module docstring, and in `--error-grace`'s help text, so a
      reader who never opens this skill still meets it.

## Quality
- [x] Frontmatter untouched. Description measured with `len()`: 1009 of 1024, unchanged, so no
      routing keyword moved and no trigger was displaced.
- [x] Stdlib only - the change is exception handling and integer arithmetic, so the script still
      imports in a bare environment, which the contribution gate needs.
- [x] `GhUnavailable` is kept apart from `GhFailed` rather than subclassed, so `except GhFailed` in
      the loop cannot silently swallow it and spend the retry budget on a missing binary.
- [x] The timeout report no longer fetches again. That request could itself fail, turning a plain
      timeout into an error naming the wrong system.
- [x] No session narrative, no scratch or temp paths, no machine-specific addresses or hostnames in
      the skill, the script, or this artifact. Verified with the address and path sweep.
- [x] Tables reformatted and the tell sweep run clean on the changed Markdown.
- [x] Full gate green with CI's dependency set: `repo-gate.py --pre-push` reports all checks passed,
      4055 passed / 13 skipped / 1 xfailed. The xfail is the documented write-then-run gap and is
      STRICT - an XPASS means the gap closed and the marker goes, rather than being re-added.
