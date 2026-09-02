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

- [x] An OBSERVED behavioural RED stands behind the change: running the pre-change procedure, the
      prune step was reached and a status-claim scan hand-rolled while `statusrot` already answered
      it - 10 uncategorised hits, all dismissed, against the tool's 19 categorised candidates and 9
      unexamined since its baseline. This is an unprimed baseline rather than a probe, which is why
      no synthetic arm replaces it.
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

## Second change: the capture carve-out in Scope

The scope rule said a nap "never reads or writes" a sibling, while step 1 (capture) routes by
SUBJECT and `meta-self-improve`'s dedup rule requires upserting an existing fact at the level that
OWNS its pointer - sometimes a sibling. The two rules could not both be obeyed, and the conflict was
silent: it appears only when a nap actually learns something about a sibling-owned fact, and the
readings diverge into either a forbidden duplicate or a dropped signal.

- [x] Scope now carves out capture explicitly, bounded to the owning level, with steps 2b-6 still
      chain-only and reading a sibling's entries to consolidate them still forbidden.
- [x] Cross-tree stays closed even to capture, because `move` cannot cross trees and a misfiled
      fact there cannot be re-homed by any later pass.
- [x] Step 1 names the carve-out at the point of use, so a reader following the numbered steps meets
      it where the decision is made rather than only in the Scope section.
- [x] The deliverables line no longer contradicts it: it now scopes "siblings untouched" to steps
      2b-6 and requires any capture write outside the chain to be named in the report.
- [x] Checked against the acceptance harness rather than assumed: `fixture_asserter.py`'s `nap`
      profile hashes sibling POINTER trees, which cannot distinguish a capture from a consolidation
      touch. It does not contradict the carve-out because `fixture_builder.py` plants no
      sibling-owned capture, so only a consolidation pass can move those hashes. The skill records
      that constraint and says to narrow the assertion, not delete it, if the fixture gains one.
- [x] The scope rung marker the family contract test requires (`ALTITUDE CHAIN ONLY`) is unchanged.

## Gaps, decided

- [x] The behavioural arm stays unrun and is DECLINED, not deferred: the lesson is in the
      always-loaded corpus on any machine carrying this memory store, so the arm cannot fail
      honestly here. The text check is the evidence.
- [x] Whether an agent OBEYS step `2b` under time pressure is not established by a text check. This
      is DECLINED as out of scope for a reorder: the ordering defect is that the step did not exist
      at a useful position, and obedience to a step that exists is the general skill-following
      problem, owned by the enforcement ladder rather than by this edit.
