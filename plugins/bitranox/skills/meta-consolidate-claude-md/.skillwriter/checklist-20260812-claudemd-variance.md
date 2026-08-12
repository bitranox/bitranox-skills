# skill-writer checklist - meta-consolidate-claude-md (add the `claudemd_variance` script)

Change: ship this skill's FIRST `scripts/`+`tests/` pair - the measurement its own Step 1
prescribes ("split every CLAUDE.md into `## ` sections, hash each body, group, and compute the
common ancestor of each group of 3+") but never shipped a tool for.

## PLAN

- [x] Skill type: procedure (measure, verify, converge, lift) gaining its FIRST shipped script,
      which closes Step 1's open end. Test approach: pytest on every pure core function
      (splitting, normalisation, hashing, common ancestor, grouping) plus the CLI contract, real
      fixture trees (including a real git repo for the gitignore claim) rather than mocks, and a
      retrieval check on the cross-reference row this same change adds to `compuse-toolbox`.
- [x] Trigger is measured, not hypothetical: two separate sessions hand-rolled this exact script
      from scratch (walk, split, hash, group, common ancestor) before this one shipped it - the
      repeated-chore signal a jig exists to close.
- [x] Checked it is not already shipped: this skill ships only `SKILL.md`, no `scripts/`. No tool
      in `compuse-toolbox` splits/hashes/groups CLAUDE.md sections or computes a common ancestor;
      `grep_all` and `git_state --files` answer enumeration/tracking questions, not this
      section-level measurement. Confirmed by the RED retrieval run below.
- [x] Scope: one script, one `tests/` dir with a `conftest.py` (this skill's first), one SKILL.md
      edit at the point Step 1 prescribes the measurement, and (in `compuse-toolbox`) a table row
      plus rationale bullet plus description clause.

## RED

- [x] 53 tests written against the tool's contract before any implementation existed. Ran
      unfiltered (no `-k`) against the bare test file with the implementation moved out of the
      way: collection failed with `ModuleNotFoundError: No module named 'claudemd_variance'` (1
      error, 0 collected, 0 passed) - genuine RED, not an assertion failure, because the module
      did not exist yet (this skill's first script).
- [x] Coverage spans: section splitting (level-2 boundary rules, level-3 nesting, indented/fenced
      false positives, trailing `##`, preamble dropped); the whitespace-normalisation definition
      (trailing whitespace and blank-line-run collapse hash the SAME, CRLF/LF hash the same, real
      content differs, INDENTATION differs - proving indentation is deliberately NOT normalised);
      `common_ancestor` (single-member = own parent dir, never root; multi-branch = true shared
      dir; a regression guard that a walk-root shortcut would still pass every other test but
      fail; a `_commonpath` injection seam proving the no-common-directory branch raises instead
      of silently answering "/"); the walk (multi-depth, `.git` pruning, custom filenames,
      symlink-loop termination, the `--max-files` bound, and - the tool's whole reason to exist -
      a REAL git repo with a REAL `.gitignore` proving the walk finds an ignored file, plus a
      `git grep` control on the same fixture showing a gitignore-aware search would miss it);
      decode-error handling (a real invalid-utf8 byte sequence is skipped, not raised); grouping
      (largest-variant share arithmetic, per-variant common ancestor, `--min-members` filtering,
      `--lift-threshold` annotation, overlapping `--root` de-duplication); and the CLI (`--json`
      envelope shape, exit codes 0/1/2, warnings on stderr even in `--json` mode, `--help`
      documenting both definitions verbatim, POSIX-style path rendering).
- [x] A dedicated test asserts `iter_claude_md` never calls `subprocess.run`/`Popen` at all
      (monkeypatched to raise if invoked) - the walk cannot inherit a gitignore-aware backend's
      blind spot because it has no subprocess dependency to begin with, proven rather than
      merely documented.
- [x] Retrieval test: see `compuse-toolbox`'s crossref checklist for the full transcript (one
      change split across two SKILL.md files, same as the `wtclean` precedent).

## GREEN

- [x] 53/53 pass locally (`uv run --with pytest python -m pytest
      plugins/bitranox/skills/meta-consolidate-claude-md/tests/ --import-mode=importlib -q`).
- [x] Mutation-checked, not just green: (1) `section_hash` changed to hash the RAW body instead
      of `normalize_body(body)` - exactly the two whitespace-normalisation tests that assert on
      trailing-whitespace and blank-line-run equality FAILED (2 failed, 51 passed), every other
      test (including the indentation-differs and CRLF tests) stayed green because they do not
      depend on the mutated branch. (2) `common_ancestor` changed to always return the FIRST
      member's own parent directory - exactly the four tests that exercise a MULTI-member group
      failed (the different-branches test, the walk-root regression guard, the `_commonpath`
      injection test, and the `analyze()` common-ancestor wiring test), while every single-member
      test correctly stayed green since that branch was untouched. Both mutations reverted after
      confirming the failures, and the suite re-ran green (53/53).
- [x] Run against real content on this machine (read-only): `--root /media/srv-main-softdev/projects`
      matched 152-153 CLAUDE.md files (small run-to-run drift from other live sessions editing the
      tree concurrently - expected on a shared checkout, not a tool defect), 555 sections, 44
      duplicate heading groups at the default `--min-members 2`. Spot-checked the "Claude Code
      Workflow" group (8/9 members in one variant, common ancestor
      `.../public`, 88.9% share): opened
      `apps/finanzonline_databox/CLAUDE.md` and `libs/lib_log_rich/CLAUDE.md` directly and
      confirmed their `## Claude Code Workflow` bodies are byte-for-byte identical.
- [x] Demonstrated the gitignore claim on the SAME real tree, not just the fixture: of the walk's
      152 matched files, 35 sit under a `.gitignore` pattern in their owning repo (confirmed via
      `git check-ignore --no-index` per file) and 13 are outside any git repo; the remaining 105
      are what a gitignore-aware `grep` would have found. So on this tree today, roughly a
      quarter of the CLAUDE.md files the tool measures would have been silently absent from a
      hand-rolled grep-based version.
- [x] Retrieval run via `bitranox:baseline-probe` against the UPDATED `compuse-toolbox` table
      (whole index shown, no tool named): the agent named `claudemd_variance` on the first try
      and quoted the row's own wording back as the match - full transcript in the crossref
      checklist.

## REFACTOR

- [x] Whitespace normalisation is precisely defined and stated in three places identically: the
      module docstring, the `--help` epilog, and this skill's Step 1 text - CRLF/CR to LF,
      trailing whitespace per line stripped, a run of 2+ blank lines collapsed to one, blank
      lines trimmed at the body's start/end. Leading INDENTATION is explicitly excluded and
      tested as excluded, because it is structure (list nesting, a code fence), not noise.
- [x] Common ancestor is precisely defined and stated the same three places: the deepest
      directory containing every member; a single member's ancestor is its own parent directory
      (never root); members sharing no directory raise a clear error rather than silently
      returning "/".
- [x] Bounded: `--max-files` (default 20,000) stops an unbounded walk with a warning rather than
      hanging silently, and the file count (`files_matched`/`files_read`/`files_skipped`) is
      always reported, in both text and `--json` output.
- [x] Cross-platform: no hardcoded `python3` (CLI-spawning tests use `sys.executable`); no
      subprocess calls anywhere in the tool itself (nothing to pass argv lists for); every file
      read uses `encoding="utf-8"` with a caught `UnicodeDecodeError` reported as skipped rather
      than crashing the run or silently replacing bytes; every path in output is rendered via
      `.as_posix()` for stable, consistent display regardless of platform.

## Quality

- [x] Present tense, no session narrative, in the skill, the script docstring, and this artifact.
- [x] Script and tests confirmed ASCII-only.
- [x] Script is import-safe (work behind `__main__`), stdlib only, PEP 723 header, no shebang -
      matching `redcheck.py` / `wtclean.py` / `newest.py`.
- [x] CLI contract: `--json` emits `{ok, command, skipped, data}`; diagnostics go to stderr in
      both text and `--json` mode; exit codes are format-independent (0 = at least one file
      found and analysed, 1 = the walk completed but matched nothing, 2 = usage/IO error) and
      identical either way.
- [x] Frontmatter `description` unchanged here (the edit is body prose, not frontmatter); still a
      single-line plain YAML scalar, still trigger-first.

## Deliverables

- [x] `scripts/claudemd_variance.py`, `tests/conftest.py`, `tests/test_claudemd_variance.py` (53
      tests), a Step 1 SKILL.md rewrite pointing at the tool, plus (in `compuse-toolbox`) a table
      row + rationale bullet + description clause.
- [x] `plugin.json` bumped 5.193.0 -> 5.194.0 (minor: a new shipped tool); `docs/skills.md`
      regenerated; `skill_triggers.json` checked - already in sync (`distill()` caps each skill
      at 14 keywords and both skills' descriptions already fill or are unaffected by the quota);
      `CHANGELOG.md` entry added.
