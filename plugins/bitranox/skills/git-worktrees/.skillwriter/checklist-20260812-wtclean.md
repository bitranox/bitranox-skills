# skill-writer checklist - git-worktrees (add the `wtclean` script)

Change: promote a personal-toolbox worktree-cleanup jig into the shared skill as its FIRST
`scripts/`+`tests/` pair, add a "Step 4: Finishing" section and a Quick Reference row, and retire
the personal copy.

## PLAN

- [x] Skill type: procedure (create an isolated workspace, set it up, verify it) gaining its FIRST
      shipped script, which closes the procedure's open end. Test approach: pytest on the ported
      core functions plus the CLI contract, real-git tests for the worktree half, and a retrieval
      check on the cross-reference row this same change adds to `compuse-toolbox`'s tool index.
- [x] Trigger is measured, not hypothetical: this skill's own Quick Reference already tells the
      reader to give each worktree its OWN `CARGO_TARGET_DIR`, and nothing in the skill ever
      reclaims it. `git worktree remove` deletes the checkout only, so the cache the skill told
      you to create outlives every cleanup and is found by running out of disk.
- [x] Checked it is not already shipped: no tool in this skill (it shipped none) and none in
      `compuse-toolbox` removes a worktree or reclaims a build cache; `git_state` is the nearest
      neighbour and answers a tracking-status question, not a disk-reclaim one. Confirmed by the
      RED retrieval run below, where an agent shown the whole index answered NONE.
- [x] Scope: one script, one tests/ dir with a conftest.py (this skill's first), one SKILL.md
      section plus one Quick Reference row plus a frontmatter description clause here, and one
      cross-reference table row plus rationale bullet plus description clause in `compuse-toolbox`.

## RED

- [x] 58 tests written against the tool's contract, weighted toward the refusals because this
      calls `shutil.rmtree` on machines whose layout is not ours. Escape shapes each SEEN to
      refuse, at the function AND through the real CLI: `..`, `../..`, `../../etc`,
      `wt-a/../../etc`, `/absolute`, `/`, `a/b`, `a\b`, `C:\Windows`, `C:topic`, empty, `.`, `~`,
      and `a\..\..\etc`. Negative controls alongside them (`topic`, `wt-topic`, `my-feature`,
      `feature_42`, `a.b` accepted; an absolute worktree path and `.worktrees/my-feature` still
      usable), so a guard that refused everything could not pass vacuously.
- [x] Two REAL defects found by these tests, both in the ported logic, both then fixed and pinned:
      (1) `wtclean ../../etc` was SILENTLY NORMALISED rather than refused - the guard ran only on
      the basename, and the basename of `../../etc` is the innocent bare name `etc`. The personal
      copy had the same defect and its tests never caught it because they only ever called
      `cache_dirs()` directly, never the CLI entry point. Fixed by checking the ARGUMENT for a
      parent reference before any topic is derived from it. (2) An `--apply` run that REFUSED a
      dirty worktree still printed `removed: <path> (worktree, dirty)` on stdout, because the
      renderer listed the worktree whenever it was not absent and never consulted the refusals.
- [x] Both fixes RED-verified against pre-fix source, not just asserted: with the argument guard
      removed, exactly the two traversal shapes that survive basename-stripping
      (`../../etc`, `wt-a/../../etc`) FAIL while the controls still pass; with the render fix
      reverted, `test_an_applied_run_never_claims_it_removed_something_it_refused` FAILS.
- [x] One test of my own was wrong and was corrected rather than the code: it matched the worktree
      path as a bare substring, and `wt-topic` is a PREFIX of `wt-topic-target`, so it could never
      fail. Re-anchored on the rendered `(worktree` marker.
- [x] Retrieval baseline (RED) run via `bitranox:baseline-probe` BEFORE this change, with the
      pre-change `compuse-toolbox` tool table shown verbatim (no `wtclean` row), NONE explicitly
      allowed, and the user's own words: "I finished a feature and deleted its worktree, but my
      disk is still almost full... Is there anything in this list for that, or should I just go
      hunting with du and rm myself?" The agent answered NONE, declined to force-fit `git_state`,
      reached for `du`/`ncdu`, and named the gap itself. That is the correct RED for a tool that
      does not exist yet, and it pins that the question is answerable and specific enough to fail.
- [x] Baseline contamination noted: none - the probe agent has no filesystem access
      (ReportFindings + Skill tools only) and was given nothing but the table text and the
      question, so it could not have discovered the tool any other way.

## GREEN

- [x] 58 pass locally (`pytest plugins/bitranox/skills/git-worktrees/tests/`); whole-repo suite
      green via `repo-gate.py --ci`.
- [x] Proven against a REAL git repo in a scratch dir, not only pytest fixtures: a real repo, a
      real linked worktree, and real multi-megabyte cache dirs, plus bystander directories that
      must survive. The dry run listed 3 items with sizes and deleted nothing (inventory identical
      before and after); `--apply` removed exactly those 3 and left every bystander, with
      `git worktree list` confirming the worktree was deregistered rather than orphaned. Separate
      arms in the same transcript showed the escaping-name refusal (exit 2, stdout empty), the
      dirty-worktree refusal (exit 1, worktree present, the uncommitted file readable afterwards),
      and the symlinked-cache refusal (exit 1, link intact, its target's contents intact).
- [x] Retrieval run (GREEN) with the SAME question and the SAME rules against the updated table:
      the agent named `wtclean` on the first try, quoted the row's own "leaves its per-topic build
      cache sitting outside it" wording back as the match, led with the dry-run form and said to
      read the paths and sizes before adding `--apply`, reached for `--cache-dir` for a
      nonstandard layout, and correctly read the "(ships in `git-worktrees`, not here)"
      parenthetical as meaning the invoke path is relative to the other skill. No rewrite needed.
- [x] SKILL.md section names the SYMPTOM (the disk stays full after the worktree is gone) and
      gives copy-pasteable invocations with real placeholder names, not just the mechanism.
- [x] Nothing site-specific baked in: the ported script and tests were scrubbed of the personal
      layout narrative (the "1-13 GB each" measured range, the "on local disk, away from the
      shared mount" description of one machine's storage, `nested-relay` topic names left only as
      neutral test fixtures), and no machine path (`/home/<user>/...`, `/media/...`) survives in
      either file.

## REFACTOR

- [x] The personal layout is no longer presented as universal. `cache_dirs()` hardcoded
      `~/wt-<topic>-target` and `~/wt-<topic>-clippy` with no way to change either. Now `--base`,
      `--prefix`, `--cache-suffix` (repeatable) and `--cache-dir` (repeatable, exact paths) all
      override it; the docstring, the `--help` epilog, the SKILL.md section and the index row each
      state that cache locations are a CONVENTION and not a discovery; and a run whose convention
      matches nothing warns on stderr naming the exact paths it checked, so a user with a
      different layout is not silently handed an empty plan. Tested both ways.
- [x] Safety added over the local copy, each with its own test: symlinked targets refused (and the
      measured `shutil.rmtree` behaviour pinned - it unlinks a symlink found INSIDE the tree
      rather than following it, so only the target itself is the danger); filesystem root, home
      directory and base-directory-itself refused; a target resolving outside `--base` refused;
      and the worktree argument put through the same guards before git is asked anything.
- [x] Uncommitted work is no longer discarded by default. The local copy passed `--force` to
      `git worktree remove` UNCONDITIONALLY, which discards modified and untracked files without
      asking. Now the state is read first with `git status --porcelain` (the same set git itself
      refuses on) and a dirty checkout is refused unless `--discard-uncommitted` is passed, which
      is the only path that forwards `--force`. An unreadable state is treated as dirty, never as
      clean. Verified that git's own refusal is a real second layer and is keyed on the exit code,
      not on its message text, which is localised.
- [x] Plan equals apply. `apply_plan()` consumes the Plan object and never re-scans: a cache
      directory created between planning and applying is proven to survive, one that vanished in
      between is reported rather than silently skipped, and `blocked_reasons()` is the single
      function both the dry run and the apply ask, so the dry run cannot promise what the apply
      then refuses.
- [x] Cross-platform work: escape shapes are checked against BOTH `PurePosixPath` and
      `PureWindowsPath` on every platform, so a drive-relative or backslash form is refused on
      Linux too (a dedicated test shows the platform-native check alone would accept `C:topic`);
      path SPLITTING stays platform-native, because a backslash is a legal filename character on
      Linux and a separator on Windows; refusals are carried as (path, reason) pairs rather than
      formatted strings, since splitting a message back on its colon would mis-handle every
      Windows absolute path; CLI-spawning tests use `sys.executable`, never a bare `python3`; and
      every subprocess call passes `encoding="utf-8"`, `errors="replace"`, an argv list and an
      explicit timeout.
- [x] Stated limitation rather than a silent assumption: on Windows a directory JUNCTION is not
      reported as a symbolic link, so the symlink refusal does not cover it. Said plainly in the
      docstring and in SKILL.md, together with the guard that does cover it (resolving a path
      follows a junction, so the "resolves outside the base" refusal catches one pointing away).
- [x] JSON envelope matches the repo's `{ok, command, skipped, data}` shape, with warnings and
      refusals in both stderr and `skipped` so stdout stays parseable; tested.

## Quality

- [x] Present tense, no session narrative, in the skill, the script docstring, and this artifact.
- [x] Script and tests confirmed ASCII-only.
- [x] Script is import-safe (work behind `__main__`), stdlib only, PEP 723 header, no shebang,
      mode 100644 - matching `redcheck.py` / `newest.py` / `diffbehave.py`.
- [x] CLI contract: `--json` emits `{ok, command, skipped, data}`; diagnostics go to stderr in
      both text and `--json` mode; exit codes are format-independent (0 = nothing blocked,
      1 = something refused or not removable, 2 = usage error) and identical either way.
- [x] Frontmatter `description` stays a single-line plain YAML scalar, still trigger-first.

## Deliverables

- [x] `scripts/wtclean.py`, `tests/conftest.py`, `tests/test_wtclean.py` (58 tests), a "Step 4"
      SKILL.md section, a Quick Reference row, and a frontmatter description clause here, plus
      (in `compuse-toolbox`) a table row + rationale bullet + description clause.
- [x] `plugin.json` bumped 5.192.0 -> 5.193.0 (minor: a new shipped tool); `docs/skills.md`
      regenerated; `skill_triggers.json` regenerated and byte-identical, because `distill()` caps
      each skill at 14 keywords and this skill already fills that quota from its description's
      opening clause; `CHANGELOG.md` entry added.
