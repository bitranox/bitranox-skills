# skill-writer checklist - devops-bmk (2026-10-22, lock-first-venv)

- [x] Change: section 1 ("The project venv") now says bmk locks the project (`uv lock`) and syncs
      the venv from `uv.lock` (`uv sync --locked`), why (a manifest install with `--upgrade` keeps a
      release newer than the `[tool.uv]` cooldown), and that it installs from `pyproject.toml`
      with `--exact --upgrade` only when no lock can be made. The env-var table says
      `BMK_NO_VENV_SYNC=1` also skips the `deps_update` re-sync (the lock is still upgraded). The
      provisioning-failure paragraph says `make test` / `make push` stop at `deps_update` when a
      venv is still there to sync, with the one `not retrying` line when provisioning already
      failed and `uv.lock` is unchanged. A table lists every `[venv]` failure header (`uv venv`,
      `uv lock` with `(exit <rc>)`, the fallback `uv pip install`, `uv sync`), with the
      no-exit-code `uv lock failed` case explained. The hand resync is the lock-first one; the
      manifest install is kept for a `[venv] uv lock failed` line only. Section 2 says the venv is
      synced from `uv.lock`. Section 4 separates `deps` (`(no output captured)` in JSON mode) from
      `deps_update` (its failure lines land in its capture).
- [x] Every claim checked against bmk source (`src/bmk/adapters/stagerunner/`):
      `venv._sync_from_lock` (`uv lock`, then
      `uv sync --locked --python <minor> --no-default-groups [--extra dev]` with
      `UV_PROJECT_ENVIRONMENT=<venv>`; the uv lock header with and without `(exit N)`);
      `venv._provision_locked` (`--python` is the minor, else the venv's interpreter; the manifest
      fallback only when `_sync_from_lock` returns None); `venv._install_from_manifest`
      (`.[dev]` then `.`, `--exact --upgrade`); `venv._create_venv` and `_report_failed_uv`
      (header strings); `venv._write_failure` (JSON: colon plus all SGR-stripped stderr, indented,
      header alone when uv printed nothing; text: header alone after live output);
      `venv._sync_extras` (`--extra dev` only when declared); `venv._lock` (the "another bmk is
      still locking" stderr line); `venv.venv_sync_disabled`; `registry._locked_project` and
      `helpers/_dependencies._upgrade_and_sync` (upgrade always runs; no retry when provisioning
      FAILED on an existing venv and the lock bytes are unchanged; failure lines to the stage sink
      in JSON mode); `registry` PIPELINES (`push` runs `deps` at order 10, then `test`, whose first
      stage runs `deps_update`); `actions.HelperAction` (no capture for `deps`).
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: `redcheck --corpus-cascade` reported STRONG inherited coverage (the bmk repo's
      CLAUDE.md teaches the lock-first sync), so a behavioural RED could not fail honestly.
      Replaced by a text check of the artifact: 11 must-contain and 5 must-not-contain claims. On
      the pre-change SKILL.md: 9 missing, 5 stale present (exit 1). On the final text: all hold
      (exit 0).
- [x] GREEN quote-back, first text: opus and haiku, seven questions (resync after a sync failure,
      resync after a lock failure, where the reason is after `not retrying`, `BMK_NO_VENV_SYNC`
      and the re-sync, why lock-first, `deps` vs `deps_update` blocks, a lock-failed line without
      an exit code). Both tiers answered all seven correctly with quotes from the pasted text.
- [x] Gaps closed after GREEN: `make push` order of `deps` and `deps_update` (now "runs it after
      its own `deps` check"); a JSON-mode header with no colon (now "stands alone when uv printed
      nothing"); whether `BMK_NO_VENV_SYNC` still upgrades the lock (now stated in the table);
      `--no-default-groups` unexplained and no Windows interpreter path (both added); the
      manifest install for a project without a `dev` extra (now `-e .`); the stage labels of the
      two blocks (now `[deps]` and `[deps_update]`); "text mode adds nothing" read against the
      `deps` text-mode advice (now scoped to a `[venv]` failure).
- [x] Re-probe on the final text, opus and haiku, six questions on the touched sentences (bare
      header, `BMK_NO_VENV_SYNC`, push order, no `dev` extra, `deps` vs `deps_update`, text-mode
      re-run). Both answered all six correctly with quotes. No new undecided gap.
- [x] Gaps declined: the fallback's success is read from the absence of a failure header (bmk
      reports failures only, by design); uv exiting non-zero with empty stderr (uv's domain);
      `BMK_NO_VENV_SYNC=1` leaving the venv behind the upgraded lock (the variable's stated
      purpose is "use the environment as-is"); a Windows form of every command (the interpreter
      path form is given once); diagnosing why `uv lock` failed (uv's stderr under the header);
      where a scrolled-away stderr lives (already: send stderr to a file); "highest" classifier
      ordering (defined in the section's version paragraphs, outside the probed excerpt).
- [x] GREEN diffed against RED both ways: the removed claims are the exact-and-upgrading sync, the
      manifest install as the general resync, and every in-process stage showing no output; all
      three are false against the code. Nothing else the old text taught is lost.
- [x] Tiers and cells: opus x2, haiku x2 (first text, final text).
- [x] Description measured: unchanged (frontmatter untouched).
- [x] Mirror: SKILL.md copied byte-for-byte from the bmk repo's copy.
- [x] Security scan: prose only; no secrets, hostnames, private paths or addresses.
