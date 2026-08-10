# checklist - a task declares its negative space and its stop conditions

Task Structure gains an **Out of scope** block carrying a reason per entry and a **STOP
conditions** block, plus a one-line seam pointer at Step 1.

## RED

- [x] Baseline dispatched on the pre-change Task Structure, sonnet, on an inert text-only agent
      type so nothing could reach a filesystem: a two-call-site extraction, a lookalike third
      file whose semantics differ, two helpers that must be composed and not changed, and a
      behaviour that must stay byte-identical.
- [x] RED result: no Out of scope section and no STOP conditions section at all. The single
      exclusion it did state, "Do not touch `src/commands/init.py`", landed inside Step 5, the
      COMMIT step - after an executor would already have done the work. The two
      compose-but-do-not-change helpers were excluded nowhere.
- [x] RED identified the live risk itself and had nowhere structural to put it. From its gaps
      list: the choice of which seeding policy becomes canonical is "a real design decision the
      plan must make explicitly ... I only guessed at it."

## GREEN

- [x] Same scenario, same model; only the Task Structure changed.
- [x] Out of scope present with four entries, each carrying a WHY, including both
      compose-but-do-not-change helpers that RED excluded nowhere.
- [x] STOP conditions present with five entries, including the risk RED could only report in its
      gaps: the assumed helper signature differing from what the earlier task actually produced.
- [x] A second run of the same arm reproduces both sections, so the edit lands reliably rather
      than once.

## REFACTOR

- [x] Every RED and GREEN dispatch asked for a `Skill gaps` section; every list recorded.
- [x] GREEN diffed against RED in both directions, and the diff found a LOSS: RED instructed "do
      not monkeypatch `resolve_shadow_config` or any of `view.py`'s internals; drive the real
      command end to end", while GREEN wrote a `patch.object` delegation test.
- [x] The loss was RE-RUN before anything was restructured, per the rule against acting on a
      single run. It reproduces: both GREEN runs write a mock-based test.
- [x] Cause located rather than assumed: the skill carries a TDD-shaped task structure with no
      test-quality guidance and no cross-reference to the skill that owns the seam question -
      measured by grep over the whole file, which matched neither a seam term nor
      `bitranox:process-test-design`.
- [x] Closed with a one-line pointer at Step 1 rather than new doctrine here, because the seam
      rule belongs to `bitranox:process-test-design` and restating it would give the reader two
      places to keep in sync.
- [x] No session narrative, no scratch paths, no machine-derived addresses or hostnames in the
      skill text or in this artifact.
