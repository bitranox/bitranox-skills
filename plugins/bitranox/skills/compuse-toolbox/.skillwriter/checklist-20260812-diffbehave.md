# skill-writer checklist - compuse-toolbox (add the `diffbehave` jig)

Change: promote a personal-toolbox differential-execution jig into the shared skill, and retire the
personal copy. Reference-skill edit plus a new tested script.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale). Test approach: retrieval - can
      an agent holding the skill pick the right jig and use it correctly?
- [x] Trigger is measured, not hypothetical: "does this behave differently" gets answered by LOOKING
      at two versions - an `ast.dump` comparison, a line count, a `grep -c` - none of which execute
      anything, so none of them can answer the question. Only differential EXECUTION can. The second
      half is the known-negative check: a hand-rolled detector verified only on cases where it
      already agrees has proved nothing.
- [x] Checked it is not already shipped: the skill named twelve tools before this change, none of
      them ran two commands on the same input and diffed what happened. `gate` is adjacent but
      answers "did this ONE command pass", not "do these TWO agree".
- [x] Scope: one script plus tests, one table row, one rationale bullet, one description clause.

## RED
- [x] 18 tests written against the tool's contract: AGREE/DIFFER on exit code, stdout, stderr
      independently; trailing whitespace is not a behaviour difference; summary counts and the
      `differing` name list; `--expect-differ` as the known-negative gate (met/unmet); two real
      subprocesses (not mocked) both when they agree and when they do not; stdin delivered to both
      sides; a command that fails to start is a DIFFER result, not a crash; non-ASCII output surviving
      utf-8 capture; a missing `--case-file` and a no-cases call are typed exit-2 errors, not
      tracebacks; the `--json` envelope shape (`ok`/`command`/`data`); the FAILED-expectation
      diagnostic reaching stderr without corrupting `--json` stdout even on failure; a JSONL case row
      carrying `name`/`stdin`/`args`.
- [x] Retrieval baseline (RED), agent given the pre-change table verbatim and the user's own words -
      "I rewrote a small script and want to check the new version actually behaves the same as the
      old one on some real inputs, not just eyeball the diff - is there already a tool for this?" -
      answered "No, there's no existing tool here for that" and proposed hand-rolling a
      subprocess-diff loop, naming the exact gap this tool closes.
- [x] Baseline contamination noted: none found - the probe was given the whole pre-change index with
      no tool named or hinted, and it correctly declined every listed tool rather than reaching for a
      near-miss (it named `gate` implicitly absent, not mis-picked it).

## GREEN
- [x] 18 pass locally (`pytest plugins/bitranox/skills/compuse-toolbox/tests/test_diffbehave.py`);
      whole-skill suite (210 tests) still green after the addition.
- [x] Retrieval run (GREEN) with the same question against the updated table: the agent names
      `diffbehave` on the first try, quotes the row's own wording back as the match, gives the exact
      `uv run scripts/diffbehave.py --a "OLD_CMD" --b "NEW_CMD" --case-file CASES.jsonl` invocation,
      and separately surfaces the `--expect-differ` known-negative mode unprompted. No rewrite needed.
- [x] Live-run against real processes, not only pytest: two independently-written implementations of
      the same "add two numbers" behaviour, run against a 3-case JSONL, reported `AGREE` on all
      three; a third, deliberately buggy implementation (rejects negative inputs) run against the
      first reported `DIFFER` on exactly the case that exposes it and `AGREE` on the other two, with
      `rc`/`stdout` shown for both sides; `--expect-differ 1` against the buggy pair exits 0 (JSON
      envelope `"ok": true`), and the same flag run against two IDENTICAL scripts exits 1 with
      "FAILED - required at least 1 case(s) to DIFFER, got 0" on stderr - the known-negative gate
      catching itself.
- [x] Description clause names the SYMPTOM (checking by eye whether an old and a new version behave
      the same, or whether a detector ever says DIFFER), not the implementation.
- [x] Nothing site-specific baked in: the ported script and tests were scrubbed of every local path
      (`/home/srvadmin/...`, `/media/srv-main-softdev/...`) and machine-specific docstring detail (an
      internal memory-store recurrence count and "highest in the store" framing that only made sense
      inside the personal toolbox); the public docstring states the rule generically instead.
- [x] Table row and rationale bullet follow the established shape; table realigned automatically.

## REFACTOR
- [x] Cross-platform fixes applied that the local, Linux-only copy lacked: `subprocess.run` in
      `_run_one` now passes `encoding="utf-8", errors="replace"` explicitly (without it, capture
      decodes with the machine's locale codec and fails differently per platform - stdout can come
      back `None` on Windows, POSIX raises past an `OSError`-only handler); `--case-file` reading
      uses a context manager and a caught `OSError` instead of a bare `open()` that would traceback
      on a missing/unreadable file; tests spawn `sys.executable -c "..."` rather than POSIX-only
      `printf`/`cat`/`true`, matching `test_gate.py`'s and `test_claim_check.py`'s own convention so
      the suite does not depend on external Unix binaries the local version happened to have.
      Command construction was already argv-list-based with no shell, so nothing changed there.
- [x] Quote-back on the contested design point: the `--a`/`--b` values stay ONE shell-quoted string
      split with `shlex` (not raw argv lists) - this matches `gate.py`'s identical `--gate` design
      already shipped in this skill, so the two tools present the same UX rather than diverging.
- [x] GREEN diffed against RED in both directions: RED's own proposed hand-roll (subprocess loop
      diffing stdout/exit code) is a strict subset of what GREEN's row delivers, plus stderr
      comparison and the known-negative gate RED never asked for.

## Quality
- [x] Present tense, no session narrative, in the skill and in this artifact.
- [x] File confirmed ASCII-only after the port (a non-ASCII test literal was rewritten as a
      backslash-u escape instead of the literal accented character, verified with a byte-level
      scan: 0 bytes above 127).
- [x] Script is import-safe (work behind `__main__`), stdlib only, PEP 723 header with no
      dependencies to declare.
- [x] CLI contract: `--json` emits `{ok, command, data, skipped}`; diagnostics (no-cases, unreadable
      case-file, FAILED-expectation) go to stderr in both text and `--json` mode so stdout always
      stays parseable; exit codes are format-independent (0 = expectation met, 1 = not met, 2 =
      usage/IO error) and identical whether or not `--json` is passed.

## Deliverables
- [x] `scripts/diffbehave.py`, `tests/test_diffbehave.py` (18 tests), SKILL.md row + rationale
      bullet + frontmatter description clause.
- [x] `plugin.json` bumped (minor: a new shipped tool); `docs/skills.md` regenerated;
      `skill_triggers.json` regenerated (byte-identical - the description edit did not change what
      that extractor keys on).
