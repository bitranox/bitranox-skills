# skill-writer checklist - process-test-driven-development (add the `redcheck` script)

Change: promote a personal-toolbox scenario-RED checker into the shared skill as a new
`scripts/`+`tests/` pair, add a "Scenario-Based RED" subsection, and retire the personal copy.

## PLAN

- [x] Skill type: reference/procedure (RED-GREEN-REFACTOR discipline) gaining its FIRST shipped
      script. Test approach: pytest on the ported core function + CLI contract, plus a retrieval
      check on the cross-reference row this same change adds to `compuse-toolbox`'s tool index
      (the index is the discoverability surface; this skill's own SKILL.md section is the usage
      surface once a reader is already here).
- [x] Trigger is measured, not hypothetical: a scenario-based RED (a prompt handed to an agent,
      not code) fails for two reasons a code RED never has - inherited coverage (the agent already
      has the lesson from its own config cascade or shipped reference material and answers from
      that) and telegraphing (the prompt names the trap or pre-diagnoses the cause). Both make a
      RED that cannot fail look exactly like a good result.
- [x] Checked it is not already shipped: neither this skill nor `compuse-toolbox` had a tool that
      inspects a SCENARIO/prompt for prior-coverage or telegraphed answers before this change;
      `claim_check` is adjacent but answers "is this text already present in these files", not
      "would an agent already know the answer from what it starts with".
- [x] Scope: one script plus tests plus a conftest.py (this skill's first, mirroring
      `compuse-toolbox/tests/conftest.py`), one new SKILL.md subsection here, one cross-reference
      table row plus rationale bullet plus description clause in `compuse-toolbox`.

## RED

- [x] 16 tests written against the tool's contract: flags a scenario a corpus document already
      teaches (inherited coverage) and does not flag an uncovered one (negative control); a
      near-miss that shares SOME vocabulary stays below the threshold, and lowering the threshold
      to the near-miss's own overlap proves the gate is load-bearing, not decorative; telegraphed
      prose is detected via marker phrases AND via answer-term overlap, and a de-telegraphed
      scenario asking the same question does not leak; common boilerplate words across a
      large (201-document) corpus do not cause a false positive, while genuinely rare/distinctive
      terms in the SAME large corpus still flag (the rarity-gate positive control); the `--json`
      envelope shape (`ok`/`command`/`skipped`/`data`), including on a typed exit-2 error (missing
      scenario file) and on a missing-corpus-directory warning that must land in BOTH stderr and
      the JSON `skipped` field without corrupting stdout; stdin input (`--scenario -`); and an
      explicit-timeout CLI spawn so a caller of this tool can never hang on it.
- [x] Retrieval baseline (RED) run via `bitranox:baseline-probe` BEFORE this change, with the
      pre-change `compuse-toolbox` tool table shown verbatim (no `redcheck` row) and the user's own
      words: "I'm about to hand a subagent a prompt that's supposed to make it take the wrong
      action... is there something in this list I can use to sanity-check it first?" - there was no
      row to find, which is the correct RED for a tool that does not exist yet; this pinned that
      the retrieval question is answerable and specific enough to fail without the row.
- [x] Baseline contamination noted: none - the probe agent has no filesystem access (ReportFindings
      + Skill tools only) and was given nothing but the table text and the question, so it could
      not have discovered the tool any other way.

## GREEN

- [x] 16 pass locally (`pytest plugins/bitranox/skills/process-test-driven-development/tests/`);
      whole-repo suite still green after the addition (verified via `repo-gate.py --ci`).
- [x] Retrieval run (GREEN) with the SAME question against the updated table (now including the
      `redcheck` row): the agent named `redcheck` on the first try, quoted the row's own "hands
      over its own answer" / "already documented elsewhere" language back as the match to the
      user's two stated worries, filled in the exact invocation from the table, and correctly
      flagged that the invoke path is relative to `process-test-driven-development`, not
      `compuse-toolbox` - matching the row's own "(ships in `process-test-driven-development`, not
      here)" parenthetical. No rewrite needed.
- [x] Live-run against the REAL shipped-skills corpus, not only pytest fixtures: (a) an
      out-of-domain scenario (a greenhouse irrigation fault) checked against all 862 real `.md`
      documents this repo ships returned `"verdict": "clean"`, exit 0 - the tool does not
      rubber-stamp every scenario as contaminated; (b) a scenario paraphrasing this repo's own
      shipped `winlog` lesson, reusing its distinctive vocabulary (`mojibake`, `iconv`,
      `tee-object`, `set-content`, `utf-16le`), checked against the same 862-document corpus,
      returned `"verdict": "inherited"` naming `compuse-toolbox/SKILL.md` with 5 shared rare
      terms, exit 1 - the detector actually detects, on a real corpus, not just its own synthetic
      fixtures.
- [x] SKILL.md subsection names the SYMPTOM ("Can It Even Fail?") and gives a copy-pasteable
      invocation with real placeholder file names, not just the mechanism.
- [x] Nothing site-specific baked in: the ported script and tests were scrubbed of every local path
      (`/home/srvadmin/...`, `/media/srv-main-softdev/...`), the "measured on <date>" incident
      narrative was rewritten as a self-contained rule (no dates, no "N RED arms passed" counting),
      and the `RARITY_MAX_FRACTION` comment's claim of a specific real corpus size and a term
      list from an unrelated real incident (robocopy/reparse-point vocabulary that did not match
      the shipped fictional test fixtures) was rewritten to reference only the shipped fixtures
      and tests, which any reader can reproduce.
- [x] Table row, rationale bullet, and description clause in `compuse-toolbox` follow the
      established shape; table realigned automatically by the repo's markdown-table hook.

## REFACTOR

- [x] Cross-platform fixes applied that the local copy either lacked or already partly had, now
      complete and matching this skill's own tests: the CLI subprocess helper in the test suite
      uses `sys.executable` (never a bare `python3`), passes `encoding="utf-8", errors="replace"`
      explicitly (without it, capture decodes with the machine's locale codec and fails
      differently per platform - stdout can come back `None` on Windows, POSIX raises past an
      `OSError`-only handler), and every subprocess spawn carries an explicit `timeout=` so a
      hung tool can never hang its caller; a dedicated test pins the timeout is actually passed.
      The core `audit()` function does no subprocess work itself (the brief's assumption that this
      tool "shells out to a test runner" does not hold for redcheck - it is pure text/set
      arithmetic - so the cross-platform work here is entirely in the test harness that spawns the
      CLI, not in the tool's own logic).
- [x] JSON envelope widened to the repo's `{ok, command, skipped, data}` shape (the local copy's
      envelope had no `skipped` field): a missing `--corpus` directory now lands in both the
      stderr warning AND the JSON `skipped` list, matching `newest.py`'s convention, with a
      dedicated test for both channels.
- [x] Test import style changed from the local copy's `importlib.util.spec_from_file_location`
      dance to a plain `import redcheck as R`, matching `diffbehave`/`newest`'s convention, via a
      new `tests/conftest.py` (this skill's first) that puts `scripts/` on `sys.path` - verified
      this does not break dataclass field resolution under `from __future__ import annotations`
      (16/16 tests pass).
- [x] GREEN diffed against RED in both directions: RED's retrieval baseline correctly found
      nothing (the tool did not exist); GREEN's retrieval run maps 1:1 onto the two leaks the
      RED prompt itself named (answer-giveaway, pre-loaded knowledge) with no unused capability
      and no gap.

## Quality

- [x] Present tense, no session narrative, in the skill, the script docstring, and this artifact.
- [x] Script and tests confirmed ASCII-only.
- [x] Script is import-safe (work behind `__main__`), stdlib only, PEP 723 header with no
      dependencies to declare (matches `diffbehave.py`/`newest.py`/`gate.py`: no shebang, no
      `dependencies = []` line, mode `100644`).
- [x] CLI contract: `--json` emits `{ok, command, skipped, data}`; diagnostics (missing corpus
      dir, missing scenario file) go to stderr in both text and `--json` mode so stdout always
      stays parseable; exit codes are format-independent (0 = clean, 1 = a leak was found, 2 =
      usage/IO error) and identical whether or not `--json` is passed.

## Deliverables

- [x] `scripts/redcheck.py`, `tests/conftest.py`, `tests/test_redcheck.py` (16 tests), a new
      "Scenario-Based RED: Can It Even Fail?" SKILL.md subsection here, plus (in `compuse-toolbox`)
      a table row + rationale bullet + description clause cross-referencing it.
- [x] `plugin.json` bumped (minor: a new shipped tool); `docs/skills.md` regenerated;
      `skill_triggers.json` regenerated (byte-identical - the description edits did not change
      what that extractor keys on); `CHANGELOG.md` entry added.
