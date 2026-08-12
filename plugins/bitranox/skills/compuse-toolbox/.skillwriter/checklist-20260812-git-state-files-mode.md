# skill-writer checklist - compuse-toolbox (`git_state.py --files` per-file classification)

Change: `git_state` answers the repo-level question (branch/sync/dirty) but could not answer the
per-FILE question - across a tree, which copies of a named file are tracked-and-modified,
gitignored, untracked, or outside any repo. This has now been hand-rolled twice in two sessions.
Adds a `--files GLOB` mode plus 16 new tests; extends the existing reference-skill row/bullet.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale) - existing pattern extended,
      no new skill created.
- [x] Trigger is measured, not hypothetical: the brief cites a real tree - 15 tracked-modified, 37
      gitignored, 22 outside any repo across 186 `CLAUDE.md` files - numbers a `git status`-based
      check could not have produced, since it reports nothing for a gitignored file and a
      tracked-clean file alike.
- [x] Checked it is not already shipped: `git_state`'s existing modes only report repo-level
      branch/sync/dirty; `grep_all` is the adjacent tool but it searches CONTENT, not per-path
      tracked/ignored status, and does not distinguish "no enclosing repo" from "untracked".

## RED
- [x] 16 tests written first, run UNFILTERED against the pre-change source: 16 failed
      (`AttributeError: module 'git_state' has no attribute 'classify_files'` and
      `SystemExit: 2` / `unrecognized arguments: --files` from argparse), 7 pre-existing tests
      still passed. Each new test pins one behaviour: all five states from one fixture repo; the
      tracked-and-ignored precedence; no-repo vs. untracked kept distinct; a repo with no commits
      yet (no HEAD to diff against); multiple repos under one root not cross-contaminating; glob
      filtering; paths with spaces/unicode/a leading dash; git-call batching bounded per repo, not
      per file; the JSON envelope; the plain tabular output; warnings/summary on stderr with
      stdout staying parseable JSON; all three exit codes (0/1/2); the `repo` field.

## GREEN
- [x] 23 pass (16 new + 7 pre-existing untouched). Full toolbox suite: 192 pass.
- [x] MUTATION CHECK (not vacuous): mutated the source twice, confirmed each mutation fails
      exactly the test built to catch it, then reverted and reconfirmed 23/23 green.
      1. Made `check-ignore` see EVERY candidate (not just the non-tracked remainder) and checked
         ignored before tracked in the classification order -> `test_tracked_and_ignored_
         precedence_tracked_wins` failed (`ignored` where `tracked-clean` was required).
      2. Made a no-repo file report `untracked` instead of `no-repo` -> `test_no_repo_is_distinct_
         from_untracked` failed the same way.
      A first attempt at mutation 1 (reordering the classification only, without widening the
      `check-ignore` input) passed ALL tests unchanged - because plain `git check-ignore` (no
      `--no-index`) already excludes tracked files from its own output by default, so the
      precedence would have held by GIT's accident, not this tool's decision, and the test could
      not have told the difference. Fixed by adding `--no-index` to `_batch_ignored` (verified via
      a scratch-repo probe first: a tracked file matching a `.gitignore` pattern is reported
      ignored WITH `--no-index`, silently excluded WITHOUT it - `git help check-ignore` confirms
      "tracked files are not shown at all ... but see '--no-index'"), which makes the
      caller-side "only ask about the non-tracked remainder" filtering the actual, testable
      enforcement of TRACKED WINS.
- [x] Self-check on real content: ran the shipped CLI (not pytest) over `public/` for `CLAUDE.md` -
      39 matches, a mix of `no-repo`/`tracked-clean`/`ignored` states matching what each path's
      actual git status is.
- [x] Known-negative scratch tree, run through the actual CLI's `--json` output (not the test
      suite): built a tree with a predicted answer for all five states plus the precedence case
      BEFORE running, then ran `git_state.py --files` and diffed the JSON against the prediction -
      exact match (clean/modified/tracked-but-ignored/ignored/untracked/no-repo all correct).
- [x] CLI contract per `every-cli-needs-a-machine-readable-mode`: `--json` envelope
      (`{"ok","command":"git-state","data","skipped"}`), warnings and the match-count summary on
      stderr (verified stdout stays pure parseable JSON even when a repo is skipped), typed
      `_GitBatchError` instead of a bare traceback on a broken repo, format-independent exit codes
      (0 matched >=1 file, 1 matched none, 2 the walk or every matched repo's git calls failed).
- [x] Cross-platform: argv lists throughout (no shell strings), `--` before every pathspec
      (verified against a leading-dash filename and one with spaces + unicode), and
      `encoding="utf-8", errors="replace"` on every NEW subprocess call this change adds (the
      pre-existing `git_state()` repo-mode call was left untouched - out of scope for this change).
- [x] Description clause added names the SYMPTOM/question ("which copies of a named file across a
      tree are tracked-and-modified, gitignored, untracked, or outside any repo"), not the
      mechanism (`ls-files --error-unmatch`/`check-ignore`).
- [x] Table row extended (not duplicated) with the new question and a real runnable
      `--files CLAUDE.md --root DIR [--json]` value; `docs/skills.md` regenerated
      (`build_skill_docs.py`, `--check` now passes) since the description changed;
      `skill_triggers.json --check` already reported in sync.
- [x] `git_state` split into its own detailed rationale bullet (previously folded into a generic
      "the others encode the trap" line), stating the tracked-wins precedence and the per-repo
      batching bound, matching the depth of the `grep_all`/`fleet_ssh` bullets it sits beside.

## REFACTOR
- [x] Repo-root discovery for `--files` costs ZERO subprocesses: it reuses the existing
      `find_repos()` downward filesystem walk plus a new pure-filesystem upward `.git`-presence
      check from `--root` itself (covers `--root` being a subdirectory INSIDE a repo, which a
      downward-only walk would miss).
      Git-call count is bounded PER REPO, not per file: at most 4 calls regardless of how many
      candidate files a repo contributes (`ls-files --error-unmatch -z --` batched with every
      candidate path; `check-ignore --stdin -z --no-index` batched with only the non-tracked
      remainder; an optional `rev-parse --verify -q HEAD` probe; `diff --name-only -z HEAD --`
      batched with only the tracked remainder) - proven by a monkeypatched call-counting test on a
      6-file fixture (<=4 calls, not the 12 a naive 2-per-file approach would spawn).
      `ls-files --error-unmatch` reads the TRACKED set off stdout rather than the exit code, since
      with several pathspecs the exit code only says "were they ALL tracked" - verified by probe
      that it does not stop at the first unmatched pathspec and still lists every match on stdout.
- [x] `import os` moved to the module's top-level imports (it was function-local inside the
      pre-existing `find_repos()`, which this change's `find_files()` also needed) - a small,
      same-file, same-area cleanup, not a change to `find_repos()`'s behaviour.

## Deliverables
- [x] `scripts/git_state.py` (`--files` mode: `classify_files`, `find_files`, `_repo_roots_for`,
      `_ancestor_repo_root`, `_owning_repo`, `_batch_tracked`, `_batch_ignored`, `_has_head`,
      `_batch_modified`, `_GitBatchError`, `_print_files_result`, `_main_files`, `main` CLI wiring);
      `tests/test_git_state.py` (+16 tests, 23 total); `SKILL.md` row + bullet + description;
      `docs/skills.md` regenerated; `CHANGELOG.md` entry; `plugin.json` bumped 5.188.0 -> 5.189.0.
