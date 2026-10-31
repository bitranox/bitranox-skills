# skill-writer checklist - compuse-toolbox (2026-10-31, gate.py verdict and summary line shapes)

Change: the `gate` row now states the exact stdout shapes gate.py prints and a grep that matches
them. Each verdict line is indented by exactly two spaces (`  [PASS] <cmd> (rc=0)` /
`  [FAIL] <cmd> (rc=N)`), a `--summary` match is indented nine spaces, and the closing line is
unindented and exactly `ALL GATES PASSED` or `GATE RED - follow-up NOT run`, followed by
`log: <path>`. The documented grep is
`grep -E '^  \[(PASS|FAIL)\] |^(ALL GATES PASSED|GATE RED - follow-up NOT run)$' out.txt`.
Also fixes a missing full stop ("a slow one Each verdict line"). gate.py itself is unchanged.

- [x] Receipt held; this agent loaded meta-skill-writer itself before the edit.
- [x] Prior coverage checked first: the row already said verdict lines are indented and gave an
      unanchored grep, but said nothing about the closing line's indentation and gave no grep for
      it.

## Claims and evidence

- [x] Verdict and closing line shapes. Ran `gate.py --log <scratch>/green.log --gate true` and
      `--gate false`, each with and without `--then true`, stdout captured with `> out 2>&1` and
      read with `cat -A`. Green stdout: `  [PASS] true (rc=0)$`, `$`, `ALL GATES PASSED$`,
      `log: <path>$` (plus `gates green -> running: true$` with `--then`). Red stdout:
      `  [FAIL] false (rc=1)$`, `$`, `GATE RED - follow-up NOT run$`, `log: <path>$`, the same
      with and without `--then`. rc 0 and 1.
- [x] The `--log` file holds neither: both logs contain only a blank line and
      `=== gate: true :: true ===` / `=== gate: false :: false ===`.
- [x] `--summary` lines are indented nine spaces: `--summary PASS --gate "echo '[PASS] fake'"`
      printed `  [PASS] echo [PASS] fake (rc=0)$` then `         [PASS] fake$`.
- [x] The documented grep, run against green.out, red.out, green.log, red.log: matches exactly
      the verdict line and the closing line in each stdout file, nothing in either log. On the
      `--summary` run it prints 2 lines (verdict + `ALL GATES PASSED`) while the unanchored
      `grep -cE '\[(PASS|FAIL)\]'` counts 2 `[PASS]` lines (verdict + summary echo), so the
      two-space anchor is what skips the echo.
- [x] Negative control: `grep -c '^\[PASS\]'` on the green stdout prints 0.
- [x] `reformat_tables.py --strict` reported Unchanged; the file has no non-ASCII byte.

## Probes (bitranox:baseline-probe, haiku, passage pasted)

- [x] RED (pre-edit row): grep given unanchored,
      `grep -E '\[(PASS|FAIL)\]|ALL GATES PASSED|GATE RED - follow-up NOT run'`; closing-line
      indentation answered "NOT COVERED. The passage gives the indentation rule only for the
      verdict lines". It also flagged that other output in the file could contain matching text.
- [x] GREEN (edited row): wrote exactly
      `grep -E '^  \[(PASS|FAIL)\] |^(ALL GATES PASSED|GATE RED - follow-up NOT run)$' out.txt`;
      (b) answered NO, quoting "the closing line is UNINDENTED and exactly `ALL GATES PASSED` or
      `GATE RED - follow-up NOT run` (with or without `--then`), followed by `log: <path>`."
      Single tier (haiku); the pass is a retrieval answer copied from the row, so no opus arm.

## Gaps declined

- Where the gate commands' own output goes with no `--log`: covered in the same row's invocation
  column ("the default log is per-invocation"), and `gate.py --help` says the default is a fresh
  per-invocation file; the measured stdout held only gate.py's report lines.
- Whether the closing line appears when the gate process dies: covered by the row's existing
  "second exit that fires when the gate process ended with NO verdict line" sentence.
- Unescaping `\|` in a table cell: the table-wide markdown convention, not this row's to restate.
- Whether stderr can carry a verdict line: the anchored grep matches only the measured shapes, and
  the row already names stdout as the verdict's stream.
