# skill-writer checklist - compuse-toolbox (add the `newest` jig)

Change: promote a personal-toolbox latest-by-mtime jig into the shared skill, and retire the
personal copy. Reference-skill edit plus a new tested script.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale). Test approach: retrieval - can
      an agent holding the skill pick the right jig and use it correctly?
- [x] Trigger is measured, not hypothetical: sorting timestamped names lexicographically picks the
      WRONG one, because a longer name sharing the same date prefix sorts AFTER a shorter one, so an
      extra word beats the date. Pruning the wrong file is loud and gets noticed; VERIFYING against
      the wrong baseline is silent, which is the dangerous half.
- [x] Checked it is not already shipped: the skill named thirteen tools before this change, none of
      them picked a path by mtime. `git_state`, `conflict_scan`, `claim_check`, `grep_all`, and
      `transfer` are the adjacent filesystem/git-facing tools, and none of them stat or sort by
      modification time.
- [x] Scope: one script plus tests, one table row, one rationale bullet, one description clause.

## RED
- [x] 15 tests written against the tool's contract: the name-sort trap reproduced and defeated (both
      as a pure-function call and end to end through the real CLI); ordering newest-first across
      three paths; a deterministic tie-break by INPUT ORDER when two mtimes are equal (not left to
      directory-listing luck); a missing path skipped, not a crash; `unreadable()` reports exactly
      the paths that could not be stat'd; directories count as well as files; `age_seconds` for a
      readable and an unreadable path; CLI usage error (no paths -> exit 2, no traceback); nothing
      readable -> exit 1; `--all` lists every match newest-first; `--json` envelope shape
      (`ok`/`command`/`skipped`/`data`); skipped paths warned on stderr AND listed in the JSON
      `skipped` field, without corrupting `--json` stdout.
- [x] Retrieval baseline (RED): dispatched a `bitranox:baseline-probe` agent with the pre-change
      13-row table (no `newest` row) and the user's own words - "I have a folder full of timestamped
      backup directories, some with longer names than others. I need to script a check for which one
      is genuinely the most recent before I prune the rest - what should I reach for?" - it answered
      "None of the listed tools fit this," walked through why each adjacent one (`git_state`,
      `conflict_scan`, `claim_check`, `grep_all`, `transfer`) does not apply, and said it would reach
      for `ls -dt` or a Python `pathlib`/`os.stat` sort instead, explicitly flagging "that's a gap if
      this is a recurring chore worth adding to the toolbox." Confirms the gap.
- [x] Baseline contamination noted: the RED probe's own hand-rolled fallback independently named the
      lexicographic-sort trap ("a longer timestamped name can sort after a shorter, more-recent one")
      before concluding no listed tool covers it - it recognized the PROBLEM from general knowledge
      but correctly declined every tool in the index rather than mis-picking a near-miss, so the gap
      is about missing TOOLING, not missing problem-recognition, and the retrieval test below is
      testing the right thing (row wording -> tool pick), not testing whether the model knows the
      underlying rule.

## GREEN
- [x] 15 pass locally (`pytest plugins/bitranox/skills/compuse-toolbox/tests/test_newest.py`); whole-
      skill suite (225 tests) still green after the addition.
- [x] Retrieval run (GREEN) with the same question against the updated 14-row table: the agent named
      `newest` on the first try, quoted the row's own "which backup/log/snapshot is the latest"
      wording back as the match, and gave the exact invocation
      `uv run scripts/newest.py /path/to/backups/nightly-* --all --json`, unprompted reasoning that
      `--all` lets you sanity-check the ranking before committing to a prune, and noted the row
      matches an existing memory rule (sort by mtime, never lexicographically) - recognizing `newest`
      as the packaged tool for it. No rewrite needed.
- [x] Live-run against real paths, not only pytest: built a scratch directory with
      `nightly-snapshot-with-extra-notes-20260708` (mtime set 10000s in the past) and
      `nightly-snapshot-20260804` (mtime now); `ls <glob> | sort | tail -1` picked the WRONG
      (older, longer-named) entry, and `uv run scripts/newest.py` on the same glob picked the
      correct, newer one and printed its age; `--json` on the same input produced a clean envelope
      with `"ok": true` and the correct single-entry `data` array.
- [x] Description clause names the SYMPTOM (picking the latest backup/log/snapshot by eye or with
      `ls | sort | tail -1`, which picks the wrong one), not the implementation.
- [x] Nothing site-specific baked in: the ported script and tests were scrubbed of every local path
      (`/home/srvadmin/...`, `/media/srv-main-softdev/...`) and the docstring's original example
      names (which referenced an internal project codename) were replaced with fully generic
      `nightly-snapshot-*` names; no memory-store bookkeeping language ("recurrence N", "highest in
      the store") carried over - the docstring states the rule as a self-contained fact instead.
- [x] Table row and rationale bullet follow the established shape; table realigned automatically by
      the docs-md-table-formatting hook.

## REFACTOR
- [x] Cross-platform fixes applied that the local, Linux-only copy lacked: the local tests relied on
      creation-order timing for two of the six original cases; the ported suite sets every mtime
      EXPLICITLY via `os.utime` (already the local convention for most cases, now applied uniformly)
      and adds a dedicated tie-break test, because mtime resolution differs by filesystem/OS and two
      files written back to back can land on an EQUAL mtime - a test depending on creation order to
      separate them would be flaky exactly when it matters. CLI-contract tests spawn the script via
      `sys.executable` (matching `test_diffbehave.py`'s and `test_gate.py`'s own convention) rather
      than assuming a POSIX shell; no external Unix binaries are invoked anywhere in the suite. The
      tool itself does no subprocess work, so the `encoding="utf-8", errors="replace"` capture
      concern that applies to `diffbehave`/`gate` does not apply here - noted and confirmed, not
      silently skipped.
- [x] Added an explicit, tested tie-break rule the local copy never defined: Python's stable sort
      keeps equal-mtime paths in INPUT order, so `newest([a, b])` and `newest([b, a])` on two paths
      with identical mtime return `a` and `b` respectively - deterministic, not directory-listing
      luck. Documented in the `by_mtime` docstring.
- [x] Strengthened the JSON contract over the local original: the local copy silently dropped
      unreadable paths with no signal at all when `--json` was used. The ported version adds
      `unreadable()`, a stderr warning naming the skipped paths, and threads them into the envelope's
      `skipped` field - consistent with `claim_check.py`'s and `git_state.py`'s existing `skipped`
      convention in this skill, rather than the local copy's silent-drop behavior.
- [x] GREEN diffed against RED in both directions: RED's own proposed hand-roll (`ls -dt` or a
      Python `pathlib`/`os.stat` sort on `st_mtime`) is a strict subset of what GREEN's row
      delivers, plus the deterministic tie-break, mixed file/directory support, age reporting, and
      the `unreadable`/`skipped`/`--json` contract RED never asked for.

## Quality
- [x] Present tense, no session narrative, in the skill and in this artifact.
- [x] File confirmed ASCII-only after the port (byte-level scan: 0 bytes above 127 in both the
      script and the test file).
- [x] Script is import-safe (work behind `__main__`), stdlib only, PEP 723 header with no
      dependencies to declare.
- [x] CLI contract: `--json` emits `{ok, command, data, skipped}`; diagnostics (no-paths, nothing-
      readable, unreadable-path warning) go to stderr in both text and `--json` mode so stdout always
      stays parseable; exit codes are format-independent (0 = a match, 1 = no match, 2 = usage error)
      and identical whether or not `--json` is passed.

## Deliverables
- [x] `scripts/newest.py`, `tests/test_newest.py` (15 tests), SKILL.md row + rationale bullet +
      frontmatter description clause.
- [x] `plugin.json` bumped (minor: a new shipped tool); `docs/skills.md` regenerated;
      `skill_triggers.json` regenerated.
