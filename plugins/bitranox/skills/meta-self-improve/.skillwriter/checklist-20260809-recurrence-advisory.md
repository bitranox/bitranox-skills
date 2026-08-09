# meta-self-improve: the engine surfaces a recorded recurrence

Scope: one sentence in step 6 documenting a new engine advisory. The behaviour change ships in
`hooks/uuid_store.py` + `hooks/memory_engine.py`, not in the skill text.

## What the tests showed

- [x] RED, code: five new tests in `hooks/tests/test_memory_engine.py` fail against the pre-change
      source (`recurrence_count` does not exist; the CLI prints no advisory). The sixth, the
      no-marker control, passes before and after - it is the negative control.
- [x] GREEN, code: 77 passed in `test_memory_engine.py`.
- [x] End-to-end against a scratch tree, not only the spy: a body carrying `recurrence: 4` prints
      the advisory; a body with no marker prints nothing; both exit 0. Exit codes captured as
      `cmd > out 2>&1; rc=$?`, never `| tail` then `$?`.
- [x] RED, skill text: DISPROVEN, and the change was cut to match. A subagent given the COMPLETE
      step 6 and a repeat-shaped scenario DID reach the jig endpoint ("a toolbox script that runs
      the four-step runbook ... since this has now been hand-done at least four times"). An earlier
      run that appeared to show a gap had been given a TRUNCATED step 6 with the
      "cross to the chore ladder" paragraph removed, so it tested text that does not exist.
- [x] Consequence recorded rather than worked around: no new rule, no new Deliverables box, no new
      Rationalizations row. The ladder needs no new instruction; what failed in practice is that
      the count sits in a body being edited for other reasons and nothing points at it. Only the
      documentation of the new advisory was added.

## Checks

- [x] Description frontmatter untouched, so the CSO lint is unaffected.
- [x] Cross-skill references by skill NAME; script references name their home.
- [x] No session narrative or private provenance in the skill text or this artifact: no operator
      instructions, no scratch paths, no "moved from" history.
- [x] Values added are generic; no address, hostname, credential or machine path introduced.
- [x] Sibling tests exist and pass for the changed scripts.
- [x] LF endings; ASCII only, no typographic tells.
- [x] Version bumped in `.claude-plugin/plugin.json` (MINOR: new capability in an existing hook).
