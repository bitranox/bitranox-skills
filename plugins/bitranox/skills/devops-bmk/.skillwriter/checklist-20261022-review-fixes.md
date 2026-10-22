# skill-writer checklist - devops-bmk (2026-10-22, review-fixes)

- [x] Change: three corrections against the code. (1) The hand resync for a project with no Python
      classifier passes the minor the venv's interpreter reports (`--python 3.10`, read from
      `.venv/bin/python --version`), never the interpreter's path, which on CPython 3.10 and older
      leaves an empty venv when uv recreates it. (2) `deps_update`'s failed block: a failed re-sync
      shows the `[venv]` report with uv's reason, a `[tool.uv]` cooldown uv refuses shows uv's
      refusal, and a failed lock upgrade is named by its step only, without uv's reason, with how
      to see that reason by hand. (3) `make test`'s first stage is `update_deps`, which runs the
      `deps_update` pipeline, so JSON mode shows `[update_deps] (exit code: 1)` with the nested
      `[deps_update]` block; `bmk deps update` / `make dependencies-update` show `[deps_update]`
      directly.
- [x] Every claim checked against bmk source (`src/bmk/adapters/stagerunner/`):
      `venv._sync_python_request` (declared minor, else the minor `venv_version` reports, else the
      interpreter path); `helpers/_dependencies._upgrade_and_sync` (the
      `<project>: uv lock --upgrade failed after the floor update` line; `lock_project` returns a
      bool, so no uv reason); `helpers/_dependencies.main` (a `SupplyChainConfigError` line goes
      to `locked.out`, carrying `uv could not resolve the cooldown: <uv stderr>`);
      `registry._TEST_PIPELINE` (`Stage("update_deps", 10, PipelineAction("deps_update"))`);
      `output.report_batch_failures` (`[<name>] (exit code: <rc>)`); `cli/commands/dependencies_cmd`
      (`deps update` runs prefix `deps_update`); the template Makefile (`dependencies-update`).
      `update_dependencies` writes the raised floors before the upgrade and nothing reverts them.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: a text check of the artifact, four claims (minor not path for no classifier;
      `update_deps` named as `make test`'s first stage; the nested block described; lock-upgrade
      failure named by step without uv's reason). On the pre-change SKILL.md all four FAIL
      (exit 1); on the final text all four PASS (exit 0). The previous text was already the
      installed version, so a no-skill behavioural arm would have measured the old text.
- [x] GREEN quote-back on the edited passages, opus and haiku, three questions (the `--python`
      value with no classifier and a 3.10 venv; the outer block name in `make test` and where the
      `deps_update` block is; whether a lock-upgrade failure shows uv's reason). Both tiers
      answered all three correctly with direct quotes. 2 tiers x 3 questions.
- [x] Gaps closed after GREEN: how to read the venv's minor (now `.venv/bin/python --version`
      printing `Python 3.10.19` means `--python 3.10`; both tiers reported it); where to run the
      manual lock upgrade and whether it sees the same manifest (now "in the project directory",
      and the raised floors stay in `pyproject.toml`).
- [x] Re-probe on the final text, haiku, two questions on the touched sentences (`--python` for a
      `Python 3.12.4` venv; where to run the lock upgrade and whether it sees bmk's manifest).
      Both answered correctly with quotes. One further narrowing after it: "re-runs the same
      resolve" became "resolves the same manifest", since a hand run lacks bmk's own-package
      `--refresh-package` flags; the text check still passes.
- [x] Gaps declined: no venv at all (nothing to resync; provisioning creates it); finding the
      classifiers and another venv path (stated elsewhere in the same section, outside the
      probed excerpt); `make push`'s `[deps]` block (already its own sentence); how the nested
      block is indented on screen (the header strings are given; layout is the engine's).
- [x] GREEN diffed against RED both ways: the removed claims are the interpreter-path request,
      "says why" for a failed lock upgrade, and the stage name `deps_update` for `make test`'s
      first stage; all three are false against the code. Nothing else the old text taught is lost.
- [x] Mirrors the bmk repo's copy byte for byte.
