# meta-dream-tree review - 2026-09-02

Change under review: the toolbox pass is split. A new step `0c` reads the tool inventory before
capture, and step `10b` becomes the CONSOLIDATE half and no longer re-runs the listing.
`references/dream-core.md` carries the split, since the family single-sources its mechanics there.

## Claim tested

The dream procedure schedules its tool inventory before the passes that consume tools, so an agent
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

Assertions covering this skill and the shared core:

- [x] a step `0c` exists;
- [x] its line position precedes step 1, so the ordering claim is checked structurally and not by
      the presence of the words;
- [x] step `10b` is named the CONSOLIDATE half;
- [x] `dream-core.md` states the pass as SPLIT and names the inventory READ;
- [x] the core's nap delta states that deferring the pass has never meant skipping the inventory.

## Quality

- [x] Step numbers are letter-suffixed (`0c`), so no existing step reference shifts; step 9,
      step 10b and step 11 still resolve for readers citing them.
- [x] Step `0c` names steps 4, 5 and 7 as the passes it protects, so the reason is at the step
      rather than only in the core.
- [x] Step `10b` no longer repeats the listing command, so the split has one owner per half and the
      mechanics stay single-sourced in `dream-core.md`.
- [x] Front matter untouched: no `name` or `description` change, so no routing keyword moved.
- [x] Present tense, no session narrative, no machine-specific paths or addresses added.
- [x] Family contract holds: `pytest plugins/bitranox/hooks/tests/test_dream_skill_contracts.py`
      passes, 11 tests, including the three single-sourcing assertions that fail when a skill
      restates a family literal from the core. Proven to discriminate by planting a banned literal
      and confirming the named failure.
- [x] Full suite green: 4216 passed, 13 skipped, 1 xfailed.
- [x] Structural gate green: `repo-gate.py --ci --no-pytest`.
- [x] No script is shipped or changed by this edit, so the bundled-script test requirement does not
      apply.

## Gaps, decided

- [x] The behavioural arm stays unrun and is DECLINED, not deferred: the lesson is in the
      always-loaded corpus on any machine carrying this memory store, so the arm cannot fail
      honestly here. The text check is the evidence.
- [x] `dream-core.md` is a reference file, not a SKILL.md, so it triggers no review artifact of its
      own. Its change is covered here because this skill owns the file.
- [x] Whether the CONSOLIDATE half at step `10b` still has everything it needs after the read moves
      away is checked by assertion, not by a run: it reads the same inventory, and the listing
      command remains documented in the core it cites.
