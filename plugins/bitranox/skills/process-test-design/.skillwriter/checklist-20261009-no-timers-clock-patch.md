# skill-writer checklist - process-test-design (2026-10-09, no timers in tests, clock patching)

Two gaps in the determinism and mocking guidance: the clock was listed as a legitimate patch edge
with no warning that the clock function is process-global, and "poll a condition with a timeout"
prescribed a timer-based wait.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Test: application scenarios (write the test) on two tiers, plus a
      coverage check against the file.
- [x] Scope: one new bullet in the mocking section, the sleep bullet rewritten, the checklist line
      split in two, one sentence in the wait-or-retry paragraph that told the reader to assert on
      elapsed time inside a test. Frontmatter untouched, so no derived artifact regenerates.

## RED
- [x] Claim verified by execution, not review: `mock.patch("time.monotonic", return_value=1000.0)`
      around `asyncio.wait_for(asyncio.sleep(0.3), timeout=2)` never returns (killed by an outer
      6 s timeout, rc 124); patching a module-level alias `_now = time.monotonic` instead lets the
      same sleep finish while the alias reads 1000.0.
- [x] `redcheck --corpus-cascade` flagged both scenarios. The clock scenario has a memory fact body
      on this machine about the asyncio freeze; the waiting scenario matched only function words in
      a large CLAUDE.local.md. Route taken: the coverage check against the file is the evidence,
      and the behavioural arms are kept as supporting evidence of what the OLD text teaches.
- [x] Coverage RED with a positive control: control `order-independent` 2; `loop.time` 0;
      `process-global` 0; `pytest-timeout` 0; `terminate-after` 0; `plant` 0; `deadline` 0;
      `Poll a condition` 1 (the line being replaced).
- [x] Behavioural RED, old excerpt, two tiers. Sonnet patched `ratelimit.bucket.time.monotonic`
      believing it module-scoped - it is the same global function, so the test hangs. Both tiers
      bounded their waits with hand-written deadlines (`done.wait(timeout=5)`,
      `worker.join(timeout=5)`, an outer `asyncio.wait_for(..., timeout=2.0)`), quoting "Poll a
      condition with a timeout". Both reported the global-versus-module choice as their own guess,
      not the text's.

## GREEN
- [x] Coverage after the edit: control 2; `loop.time` 1; `process-global` 2; `pytest-timeout` 1;
      `terminate-after` 1; `plant one` 2; `Poll a condition` 0; `Assert on elapsed` 0.
- [x] Behavioural GREEN, same scenarios, new excerpt, both tiers: sonnet replaced the consumer module's `time` name
      with a stub and did not touch `time.monotonic`, quoting "never the function on the time
      module"; waited with a plain `jobs.join()` and a plain `thread.join()`, naming the runner's
      per-test timeout as the wedge catcher. Haiku did the same: a module-scoped `time` proxy that
      forwards every other attribute, `jobs.join()` and `thread.join()` with no timeout.
- [x] Every dispatch asked for a `Skill gaps` section; lists recorded below.
- [x] Diffed GREEN against RED both ways: RED's correct choices (inject when you own the code,
      task_done after the write, real queue not a mock) all survive in GREEN; nothing lost.

## Gaps and decisions
- [x] Closed: a `time` stub exposing only `monotonic` breaks the consumer's other `time.*` calls -
      the text now says the stub keeps the rest of `time`.
- [x] Closed: the text leaned on "the runner's per-test timeout" without saying one must exist -
      it now says to configure one suite-wide if the project has none.
- [x] Declined: which tier owns a real-seconds check of a time window. That is the existing
      integration/e2e guidance; the rule here governs waits inside a test.
- [x] Declined: vendored code that itself waits on a real asyncio timer. That is code under test
      with its own timeout, already covered by "driven by injecting its clock, not by waiting it
      out"; a library with no clock seam is out of this skill's scope.
- [x] Declined: guessed module and class names - an artifact of the scenario, not of the text.
- [x] Quote-back: "Never patch the clock function itself: it is process-global, and the runtime's
      own timers read it." and "Let the runner's per-test timeout (pytest-timeout, nextest
      `terminate-after`, the framework's test timeout) catch a wedge instead of a deadline written
      into the test."

## Consistency sweep
- [x] Whole skill dir searched for sleep/poll/timeout/clock/deadline/wait. "Wait on whatever lands
      LAST" already names a producer signal; "slow the clock it races" is reproduction apparatus (a
      framework tick), not a clock patch; the description keeps its `sleep` keyword unchanged.

## Quality
- [x] Present tense, language-neutral rule with one Python example; no session narrative, no
      machine paths or addresses in the skill.
- [x] Frontmatter untouched; `docs/skills.md` and `skill_triggers.json` need no regeneration.
