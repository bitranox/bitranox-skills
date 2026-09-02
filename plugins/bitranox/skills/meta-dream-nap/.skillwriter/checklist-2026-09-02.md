# meta-dream-nap review - 2026-09-02

Change under review: the toolbox pass is split, and the inventory READ moves to a new step `2b`
between backup and dedup. The CONSOLIDATE half stays deferred. A deliverables checkbox and two
rationalization rows enforce it.

## Claim tested

The nap procedure schedules its tool inventory before the passes that consume tools, so an agent
following the numbered steps reads the inventory before it can hand-roll a scan a shipped tool
already implements.

## How it was tested

The behavioural arm is NOT usable here and was not run. `redcheck --corpus-cascade` over the
directory a dispatched agent would inherit reports STRONG inherited coverage against 987 corpus
documents: the tree-top memory index already states this lesson, so an agent reaching it answers
from there rather than from the scenario, and the RED cannot fail honestly. Route taken, per the
skill's stated alternative: a text check of the artifact, which inherited context cannot satisfy.

The check asserts ten properties across the three changed files and is run twice - against the
pre-change revision and against the change - requiring the first to FAIL and the second to PASS.

- [x] RED: the pre-change revision fails all 10 assertions.
- [x] GREEN: the change passes all 10.
- [x] The check discriminates: a run where the pre-change revision passes is reported as INVALID
      rather than as a pass, so a vacuous assertion set cannot read as success.
- [x] The check caught a real defect in its own first draft (an assertion looking for a phrase the
      file does not use), which was corrected against the file rather than by weakening the check.

Assertions covering this skill:

- [x] a step `2b` exists;
- [x] it reads the toolbox inventory;
- [x] its line position precedes the dedup step, so the ordering claim is checked structurally and
      not by the presence of the words;
- [x] the deliverables list requires the read before dedup/placement/prune;
- [x] the deferred list defers the CONSOLIDATE half only.

## Quality

- [x] Step numbers are letter-suffixed (`2b`), so no existing step reference shifts; external
      references to steps 3 through 6 still resolve.
- [x] Front matter untouched: no `name` or `description` change, so no routing keyword moved.
- [x] Present tense, no session narrative, no machine-specific paths or addresses added.
- [x] Family contract holds: `pytest plugins/bitranox/hooks/tests/test_dream_skill_contracts.py`
      passes, 11 tests. That test is proven to discriminate by planting a banned family literal in
      this file, confirming it fails naming this file, and restoring.
- [x] Full suite green: 4216 passed, 13 skipped, 1 xfailed.
- [x] Structural gate green: `repo-gate.py --ci --no-pytest`.
- [x] No script is shipped or changed by this edit, so the bundled-script test requirement does not
      apply.

## Gaps, decided

- [x] The behavioural arm stays unrun and is DECLINED, not deferred: the lesson is in the
      always-loaded corpus on any machine carrying this memory store, so the arm cannot fail
      honestly here. The text check is the evidence.
- [x] Whether an agent OBEYS step `2b` under time pressure is not established by a text check. This
      is DECLINED as out of scope for a reorder: the ordering defect is that the step did not exist
      at a useful position, and obedience to a step that exists is the general skill-following
      problem, owned by the enforcement ladder rather than by this edit.
