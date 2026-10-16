# skill-writer checklist - devops-bmk (2026-10-17, fold23)

- [x] Change: section 1 names a `ModuleNotFoundError` inside bmk's own dependencies as bmk's shared
      env (`bmk_selfcheck` repairs it on the next `make`) and says the "waited 10s for the lock ...
      gave up. Nothing was changed." line speaks only for the skipped upgrade; the project-venv
      section says a version mismatch is cured by the next sync, not by deleting `.venv`, how to
      see a failed sync, and that a hand `--exact` resync must name every extra; section 3 says
      `release` tags the version already in `pyproject.toml` and pushes branch then tag, `push`
      commits with `git add -A` (empty commit when nothing is staged), and the `deps` stage fails
      with `(no output captured)` on a floor behind a fresh PyPI release; section 4 says an
      in-process stage shows nothing captured in JSON mode; section 6 says `test-all` is the only
      cross-version run of `local_only` tests and explains exit 5 on an empty integration lane.
      Three new Troubleshooting rows; two rows no longer prescribe `rm -rf .venv`.
- [x] Corrections found while verifying against bmk's source: the shell-lint gate runs
      `shfmt -d -i 4 -bn -ci` (the text omitted `-bn`) and takes bashate's line length and ignores
      from `[tool.bashate]` (the text said no config is read; that holds for bashate itself, not
      for bmk's call); the Makefile no longer passes `--refresh-package bmk`; the `bmk ensure`
      block moved under the sentence that introduces it.
- [x] Every claim checked against bmk 3.21.2 source: `bmk_toollock` (the gave-up line, `--on-timeout
      skip` for the upgrade), `bmk_selfcheck`, `registry.py` (push pipeline starts with `deps`; the
      test pipeline's first stage is `deps_update`), `_dependencies.print_report` (returns 1 on an
      outdated floor), `git_ops.py` (`add -A`, `--allow-empty`), `_release.py` (pushes branch, then
      tag; refuses a dirty tree), `tools.integration_pytest_argv` (no exit-5 special case),
      `_shellcheck.py` (shfmt argv, bashate flags and the 120/`E003` fallback). The `deps` claim
      was also run: an outdated floor in a scratch project failed `bmk deps` with
      `(no output captured)` in JSON mode, and text mode printed the report above it.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact, behavioural RED replaced because the rules sit in the
      always-loaded memory index of the authoring machine): a fresh verifier answering only from
      the pre-change text found NONE for the exit-5 case, could not explain the `deps` failure,
      answered the version-mismatch case with `rm -rf .venv && make test`, and had to infer the
      lock line and the no-bump-before-release rule.
- [x] GREEN quote-back, two rounds, each on opus and haiku, answering from the skill file only:
      round 1 seven scenarios, round 2 the six the refactor touched; every answer quoted the
      governing text, and every round-1 quote was substring-checked against the file (12 of 12).
- [x] Gaps closed: exit 5 called both a failed stage and nothing to run (now: the red is not a test
      failure, and push/ship/release do not run the lane); how to see a failed sync; which venv a
      hand resync targets (including `UV_PROJECT_ENVIRONMENT`); whether `release` pushes the commit;
      the second cause of a stale bmk (a skipped upgrade under the tool lock); the stale
      `--refresh-package` row; the misplaced `bmk ensure` block.
- [x] Gaps declined: what to do if the re-run after a `ModuleNotFoundError` fails again (the repair
      path fails loudly on its own); how to list a project's extras and check an env var (general
      knowledge, not bmk); which `.sh` files the gate lints (unchanged, out of scope); push failures
      during `release` (git's own messages); `--human` coverage per command (section 4 already
      states the precedence).
- [x] GREEN diffed against RED both ways: no RED answer lost; RED's mention of `make ship` as an
      alternative to `release` is still in the command table.
- [x] Description measured: unchanged (440 characters)
- [x] Mirror: byte-identical to the tool repo's `skills/devops-bmk/SKILL.md`
- [x] Security scan: prose only; no secrets, hostnames, private paths or addresses
- [x] Follow-up (9.2.4 / bmk 3.21.4): the exit-5 text said `make testintegration` exits 5; make
      exits 2 after `Error 5` and only bmk exits 5, so the text now keys on the
      `[pytest_integration] (exit code: 5)` line. A declined round-2 gap (integration tests exist
      but none were collected) is now closed: that case is a filter fault, not an empty lane.
      Quote-back on opus and haiku for the three exit-5 scenarios.
- [x] Round-3 gap closed: `testintegration` passes a fixed `-m integration`, so "the marker
      expression" was not a cause a reader can change; the text now names the diagnostic
      (`pytest --collect-only -m integration`) instead. Declined: where to report an empty lane
      (the caller's own reporting), dynamically added markers and tests outside `tests/` (the
      collect-only command covers both), how a caller keeps an exit-5 lane from going red (the
      caller's choice).
