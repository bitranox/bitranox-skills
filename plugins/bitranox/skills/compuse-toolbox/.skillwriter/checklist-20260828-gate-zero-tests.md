# compuse-toolbox: the `gate` row gains the per-invocation log and the zero-test refusal (5.269.0)

Skill type: REFERENCE (a routing table over bundled scripts). The row changes because the tool it
routes to gained two behaviours a caller must know about before trusting a green gate.

**Ordering, stated plainly: this review is RETROSPECTIVE.** The row was authored alongside the code
change, and the checks below were run afterwards, against the already-written row. The Iron Law's
remedy for an untested skill edit is to delete it and start over; that is not what happened here,
and the phases below record what was VERIFIED, not an order that was followed. The verification
itself stands on its own - the accuracy check, the executed behaviour and the control are
reproducible from the shipped files by anyone, independent of when the row was written. What a
retrospective review cannot provide is the RED signal: evidence that the row's wording was shaped
by watching an agent fail without it. It was not, and no claim here should be read as saying so.

## PLAN

- [x] Skill type identified: reference/hub. One row in an existing table, no new skill, no new
      supporting file.
- [x] Test approach chosen: the behavioural arm is NOT available on this machine (see RED), so the
      evidence is a coverage and accuracy check against the shipped files, plus EXECUTION of the
      documented behaviour with a control that must answer differently.
- [x] Scope: one table row, one script, its tests, one CHANGELOG entry.

## RED - the behavioural arm is unavailable, and the route taken instead

- [x] `redcheck --corpus-cascade` over the repo: **INHERITED COVERAGE, evidence STRONG**, 875
      documents read. The always-loaded memory index on any machine carrying this store already
      states the rule ("make a gate report how much it examined, and treat zero as a refusal"), so a
      dispatched agent is handed the lesson before the scenario reaches it and a baseline cannot
      fail honestly.
- [x] Route taken, per the skill's instruction for inherited coverage: **the coverage check against
      the artifact replaces the behavioural RED.** A text-and-execution check of the shipped files
      cannot be answered from inherited context, because it asserts on what the files DO.
- [x] No pressure scenario was dispatched. Dispatching one would have produced a pass that
      described the machine's memory index rather than this row.

## GREEN - accuracy, coverage, and execution

- [x] ACCURACY (table -> file): every behaviour the row claims is present in `scripts/gate.py`:
      `default_log_path`, `observed_test_count`, `mkstemp`, the cargo `running` shape, the pytest
      `selected` shape, and `test_count` on the result.
- [x] COVERAGE (file -> table): the row names both failure modes in the words a reader searches
      with - a shared default log two concurrent runs append to, and a filter matching ZERO tests
      that exits 0 and reads as a pass.
- [x] EXECUTED, not reviewed. A runner that exits 0 having run nothing is refused:
      `[FAIL] ... (rc=0) [0 tests]`, `REFUSED: ran 0 tests`, `GATE RED - follow-up NOT run`, the
      `--then` command did not fire, gate exit 1.
- [x] CONTROL that must answer differently: the same tool on a real 2-test run reports
      `[PASS] ... (rc=0) [2 tests]` and runs the follow-up. A check that cannot report both
      outcomes proves nothing.
- [x] Per-invocation log EXECUTED: two runs in the same shell produced two different log paths,
      each carrying its own pid and a distinct random suffix. The previous fixed default is gone.

## REFACTOR - gaps found by running it, closed or declined

- [x] **FOUND, then DECLINED as correct behaviour** - `pytest -q` is NOT recognised, so no count is
      printed for it: under `-q` pytest prints neither a `collected` nor a `selected` line, only
      `2 passed`. The safety property still holds, because a `-q` run that matches nothing exits 5
      and the gate fails on the status. Recognising `N passed` instead would misread a linter's
      `Found 0 errors.` as a zero-test run, which is the looser matcher the implementation
      deliberately rejects.
- [x] **DECLINED, recorded as a known limit** - a test runner that is neither cargo-shaped nor
      pytest-shaped (for example jest, go test, vitest) returns "not applicable" and is judged on
      exit status exactly as before. This is the deliberate `None` versus `0` split: defaulting an
      unrecognised gate to zero would fail every lint and build gate in every caller's pipeline.
      Extending the recogniser is a separate change with its own tests.
- [x] The zero-test refusal is a BEHAVIOUR CHANGE for callers: a gate that legitimately runs no
      tests now fails where it previously passed. Shipped with no opt-out flag on purpose, since a
      flag would recreate the false green under a sanctioned name.

## Quality

- [x] No narrative or private provenance in the row or this artifact.
- [x] Every value in the shipped files is generic.
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over `scripts/gate.py`, `tests/test_gate.py` and this artifact: no matches.
- [x] Cross-platform: `mkstemp` passes no `dir=`, so the temp directory resolves at call time and
      `TMPDIR` is honoured rather than frozen at import.
- [x] Import-safe, stdlib only, run-time work behind the main guard.
- [x] ASCII, LF line endings, index mode `100644` (interpreter-run, no shebang).
- [x] Security review of the diff: no secrets, credentials, hostnames, addresses or PII; no
      `eval`/`exec`, no `shell=True` on untrusted input.

## Tests

- [x] `tests/test_gate.py`: 54 passed, 1 skipped. 15 new tests; 12 were watched fail against the
      pre-fix source run from a scratch copy, so the baseline could not be contaminated by the fix.
- [x] 3 of the 15 are controls that pass before AND after: `--log` still pinning an explicit path,
      a non-test gate still passing, and a linter reporting `Found 0 errors.` not being read as a
      zero-test run.
- [x] One earlier draft asserted the shared log corrupted `--summary`. That was vacuous, because
      summary lines come from the gate's captured stdout and never touch the log, so it passed
      against the unfixed source. It now asserts on the log FILE and carries a premise check.
- [x] Whole-repo gate green: `repo-gate --ci` rc 0, `repo-gate --mirrors` 0 of 11 pairs drifted.
      Full suite 3643 passed, 7 skipped.

## Deployment

- [x] MINOR bump to 5.269.0: a backward-compatible capability addition to a bundled script.
- [x] CHANGELOG entry under 5.269.0, which also backfills the 12 released versions that had no
      entry at all (5.254.0 through 5.262.0). 5.264.0, 5.265.0, 5.265.1, 5.265.2, 5.266.1 and
      5.268.0 remain missing and are named as such rather than left to read as complete.
- [x] Skill count unchanged, so the README counts need no edit.
