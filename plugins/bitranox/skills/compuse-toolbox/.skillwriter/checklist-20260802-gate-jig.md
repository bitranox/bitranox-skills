# skill-writer checklist - compuse-toolbox (2026-08-02, the `gate` jig)

Change: adds a ninth jig, `scripts/gate.py`, with its tests. It runs each gate with no shell and no
pipe, so the reported status is the gate's own, logs output, greps the summary from that LOG
afterwards, and runs `--then` only on a real pass. The plugin already BLOCKED the masked form
(`hooks/block-masked-gate-exit.py`); this supplies the safe form it leaves the reader without.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] RED, capable tier: given the pre-change skill, a `sonnet` agent hand-rolled a 12-line block
      with two temp files and per-gate `rc=$?` capture. Correct, but nothing in the skill offered
      it, and its own gaps list flagged that on a collection-time crash "the last log line is a
      traceback fragment, not a paste-worthy summary".
- [x] That baseline PASS was investigated rather than trusted, per "a baseline that passes is a
      result to investigate". It quoted a memory slug never supplied to it, which is the documented
      contamination tell, so it was re-run on a weak literal tier.
- [x] RED, weak tier (`haiku`): answered `pytest -q && ruff check src && git push` and asserted
      "`pytest -q` already outputs only the summary line - no scroll needed. If passing, it prints
      exactly one line". That is false, and it left the stated requirement unmet - it offered no
      command to capture the summary at all, only "copy the last line you saw".
- [x] GREEN, same weak tier and same scenario: reached for `gate` and gave the exit-status reason.
- [x] GREEN's gaps list worked as REFACTOR input rather than being read as a pass. It reported not
      knowing whether two gates need two invocations, and chained two with `&&` - worse than the
      one-invocation form the tool supports. The Invoke cell now shows `--gate C [--gate C ...]`.
- [x] Fix verified by quote-back: re-asked, the agent answered ONE invocation and quoted the exact
      table line, rather than reasoning it from the tool's name.
- [x] Two gaps DECLINED with reason: a concrete `--summary` regex example, and whether `--summary`
      prints to stdout. Both are per-tool argument detail, which this skill routes to `--help` by
      its own stated convention ("Per-tool arguments live in each tool's `--help`").
- [x] The documented command executed for real, not reviewed: two gates plus `--then`, green ->
      `--then` ran, red -> `GATE RED - follow-up NOT run`. Exit status measured WITHOUT a pipe
      (1 on red, 0 on green) - measuring it through `| tail` first reported the pipe's 0, which is
      the trap the jig exists for.
- [x] Tests ported with the tool (36 cases) and passing under the CI dependency set. `sys.path`
      comes from the skill's `tests/conftest.py`, so the local hard-coded insert was dropped.
- [x] Tool is generic: the docstring's build-system examples were replaced with `pytest`/`ruff`,
      and a grep for machine paths, hostnames and local tooling returns nothing.
- [x] No session narrative or private provenance added; no machine paths added.
