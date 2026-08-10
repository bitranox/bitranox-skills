# checklist - surface the decisions that are not settled

New skill. Asks, after work, which decisions the agent is NOT confident about, and suppresses the
ones that are already right. Fired automatically by a Stop hook; reachable from three skills.

## RED

- [x] Baseline run clean-room: headless, cwd OUTSIDE the knowledge tree, so no `CLAUDE.md`
      cascade or memory index is loaded. Earlier in the same session an in-workspace probe cited a
      project its prompt never named and echoed a fixture's own wording, which is what a
      contaminated baseline looks like.
- [x] Run on `haiku` AND `sonnet`. The literal tier is the one that matters: the store records
      three `sonnet` baselines passing a different skill only by reasoning AROUND its literal
      text, while `haiku` obeyed it and missed a live SEVERE.
- [x] Scenario is a described work session of ten steps holding four genuinely unsettled calls
      (a new config default that changes behaviour on upgrade, a declined override flag, a
      minor-vs-patch version bump, a flaky test waved off) mixed with clearly-right ones (tests
      added, a regex hoisted out of a loop, the gate run before pushing). Which were close calls
      is never stated.
- [x] **RED RESULT: the baseline PASSED, on both tiers.** `haiku` returned the four unsettled
      calls and none of the settled ones. `sonnet` returned five, including one the scenario did
      not plant: that the fix REPLACES the old bus-detection mechanism rather than extending it,
      so devices the old path handled may regress.
- [x] Conclusion drawn from that, not around it: the question needs no strengthening, so it ships
      VERBATIM in a fenced block. The suppression clause was already load-bearing and already
      worked; rewriting it would have been an unmeasured change to a measured-good prompt.

## GREEN

- [x] What the RED proved missing was never the wording - it was that nothing fires the question.
      So the shipped mechanism is the Stop hook, and the skill is its single source of truth.
- [x] The hook's policy is one pure function, `should_ask(touched_count, was_asked, min_paths)`,
      tested directly; the wiring is tested end to end through the real signals module with `HOME`
      redirected, so the flag file under test is the real one.
- [x] Mutation-verified rather than assumed: dropping `and not was_asked` from the policy is
      killed by two tests, including the end-to-end "the second turn must not re-ask". A guard
      whose test survives its own removal is not a guard.
- [x] `USERPROFILE` is set beside `HOME` in the fixture. `Path.home()` reads `USERPROFILE` on
      Windows, so patching only `HOME` passes on Linux and writes into a real home on Windows.

## REFACTOR

- [x] Both RED dispatches asked for a `Skill gaps` section; both lists recorded. `sonnet` reported
      it was reasoning purely from the narrative with no repo to check - true, and inherent to a
      described-session scenario. Declined: the skill runs against a session the agent actually
      performed, where that limit does not apply.
- [x] The guard is keyed by SESSION, not by project. A per-project flag outlives its session and
      demands work for something that happened in a different one; a test asserts an older
      session's flag does not suppress this one.
- [x] The false-positive side is tested, not just the true-positive one: a session that wrote one
      file produces no nudge. A gate that fires on a question is one the user turns off.
- [x] Three entry points, one ask - the guard is what makes the three-way routing safe rather than
      three-times noisy.
- [x] Boundaries stated in the body against both neighbours, since all three fire near the end of
      work: verification-before-completion asks whether a claim is TRUE, this asks whether a
      choice was RIGHT; meta-self-improve writes durable memory, this writes none.
- [x] No session narrative, no scratch paths, no machine-derived addresses or hostnames in the
      skill text or in this artifact.
