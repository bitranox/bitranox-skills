# skill-writer checklist - devops-bmk (2026-10-27, release worktree recipe and serial-run rules, bmk 3.30.0)

Twin sync of bmk's own devops-bmk copy for bmk 3.30.0. Two passages changed, nothing else:

- section 3, a new release bullet: when someone else's uncommitted edit blocks `release`, release
  from a clean worktree ON the branch (`git worktree add -f`); a detached HEAD is refused before
  anything is tagged; `release` never rewrites the Makefile;
- the parallel-pytest paragraph: a floor failure prints the report table in JSON mode too, then
  `[coverage] Coverage is below fail_under = <N>`; `workers = 1` means one process also against a
  `-n` in the project's `addopts` (bmk adds `-n 0`), and a venv without pytest-cov is kept to one
  process the same way.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which command, which refusal line, which
      output, how many processes, answered from the text.
- [x] RED by text check against the pre-change file: no line names `git worktree add -f`,
      `[release] HEAD is detached` or `-n 0`, and the old floor sentence says JSON mode shows only
      the exit line.
- [x] Claims checked against bmk's source in the same change, each read at the deciding line:
      - `release` skips the Makefile rewrite: `_SKIP_MAKEFILE_CHECK = {"install", "release",
        "rel", "r"}` gates the check in `adapters/cli/root.py`.
      - detached refusal: `helpers/_release.py` refuses `rev-parse --abbrev-ref` answering `HEAD`
        with `[release] HEAD is detached: ...` before the tag step.
      - `-n 0`: `helpers/_parallel.py` `xdist_args("1", ...)` returns `["-n", "0"]` when xdist is
        loaded and the project passes its own `-n`, else nothing.
      - no pytest-cov gives one process: `helpers/_coverage.py` returns `WorkerPlan("1", ...)`
        unless the probe says `ParallelSupport.READY` (both plugins loaded), and the `workers == "1"`
        branch runs `coverage run ... -m pytest` plus `xdist_args("1")`.
      - floor table in JSON mode: the quiet branch of the coverage report captures the output and
        writes it out when the return code is non-zero, then prints
        `[coverage] Coverage is below fail_under = <N> (exit <rc>)`.
      All true; nothing corrected.
- [x] GREEN by quote-back on the new text (opus at effort medium, plus haiku; 6 questions each,
      the two passages pasted as the text under test): every answer correct and a direct quote,
      no NONE, no contradiction. All 6 governing quotes found verbatim in SKILL.md
      (whitespace-normalised substring check); a planted invented sentence came back MISMATCH.
- [x] Gaps, each decided (nothing is changed in the twin alone, it must match bmk's copy):
      - no command given for removing the worktree (both tiers) - DECLINED: `git worktree remove
        <path>` is plain git, outside a bmk skill's scope.
      - which directory `git worktree add` runs from, and that the version commit must already be
        on the branch (opus) - DECLINED, covered: the first bullet of the same list says `release`
        tags "the version already in `pyproject.toml`, on HEAD", and any checkout of the repo works.
      - whether a detached refusal pushes anything (opus) - DECLINED: "refused before anything is
        tagged", and in `_release.py` `release()` the detached refusal returns before the
        `[release] Pushing branch` step and before any tag call.
      - "otherwise it runs serially" vs "kept to one process the same way", and whether "a parallel
        run" excludes the workers = 1 / no-pytest-cov cases (both tiers) - DECLINED: both tiers
        read it correctly (one process, `-n 0` against an `addopts` `-n`), which matches
        `xdist_args`; the serial argv is an implementation detail no reader action depends on.
      - whether `--cov`/`--dist` are passed when workers = 1 (opus, haiku) - DECLINED, covered:
        "Coverage, `fail_under` and `coverage.xml` come out the same either way".
      - whether a test failure prints the coverage table, and exit codes per failure type -
        DECLINED: predates this change; `[coverage] Tests failed` is the line a reader keys on.
- [x] Re-probe: no fix was made, so the GREEN run above is the final-text run; no undecided gap.
- [x] Tiers: opus + haiku, 2 cells, 6 questions each.
- [x] Description unchanged - no routing keyword moved.
- [x] Added lines: no address, MAC, hostname or machine path; ASCII only; the version-history
      finder finds nothing. Lines come byte-identical from bmk's copy (the twin must match).
