# bitranox-skills

Maintainer notes for this repo. This repo is both a Claude Code plugin marketplace
(`.claude-plugin/marketplace.json`) and the single plugin it ships (`plugins/bitranox/`).

## Do not rewrite history - `master` is force-push protected

Because this repo is a published marketplace, its history must stay **append-only**. Rewriting it
(squash, `git push --force`) breaks `/plugin marketplace update` for everyone who already added the
marketplace: Claude Code keeps a clone at `~/.claude/plugins/marketplaces/bitranox-skills` and the
update is a `git pull` there, which cannot fast-forward a rewritten history - so the update silently
does nothing and existing installs stay on the old version.

Ship changes with normal additive commits and a `version` bump in
`plugins/bitranox/.claude-plugin/plugin.json`.

`master` enforces this with GitHub branch protection: `allow_force_pushes: false`,
`allow_deletions: false`, `enforce_admins: true` (normal additive pushes stay free, no PR or
status-check requirement). Re-apply if it is ever cleared:

```bash
echo '{"required_status_checks":null,"enforce_admins":true,"required_pull_request_reviews":null,"restrictions":null,"allow_force_pushes":false,"allow_deletions":false}' \
  | gh api -X PUT repos/bitranox/bitranox-skills/branches/master/protection --input -
```

If a clone ever diverges (e.g. after an old force-push), recover by re-cloning, not merging:
`git reset --hard origin/master` in the marketplace clone then re-extract the version dir, or have
the user run `/plugin marketplace remove bitranox-skills` then
`/plugin marketplace add bitranox/bitranox-skills`.

## Authoring hooks and bundled scripts: keep them cross-platform

Any script this plugin ships (a hook command, `run-python.sh`, a skill's `scripts/`, a `.py`/`.js`
helper) runs on user machines that may be Windows. Author every such script so a Windows install
does not silently break it. These rules are enforced/encoded by `.gitattributes` and
`hooks/run-python.sh`; keep them intact and apply the same pattern to any new script.

- **LF line endings, always.** `.gitattributes` pins `*.sh`/`*.py`/`*.json` to `eol=lf`. A CRLF
  `.sh` makes Git Bash on Windows fail (`cannot execute: required file not found` / `$'\r':
  command not found`), which silently disables a hook. Never remove those `.gitattributes` rules;
  `git add --renormalize .` after touching them.
- **Force UTF-8 in launched interpreters.** A non-UTF-8 Windows locale (e.g. German cp1252)
  corrupts IO. The shim exports `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`; Python code opens
  files with explicit `encoding="utf-8"`.
- **No portable interpreter name.** On Windows `python3` is usually the Microsoft Store stub
  (exits non-zero), `python` may be Python 2, `py -3` is Windows-only. Launch Python through
  `run-python.sh`, which probes `python3 -> python -> py -3` and `cygpath`-converts POSIX paths.
  Do not change that probe order or the path conversion.
- **Git Bash only on Windows; never WSL/Cygwin.** The shim guards `uname -s` and skips loudly to
  stderr under an unexpected shell. A hook must never wedge a turn: every failure path exits 0.

When a learning here applies beyond this repo (it usually does), it also belongs in the shared
`skill-writer` skill's "Bundled scripts and hooks: keep them cross-platform" section.

## Every shipped Python script needs sibling tests

Any `.py` this plugin ships - a `skills/<skill>/` script OR a `hooks/` script - must have tests in a
sibling `tests/` dir: a `conftest.py` that puts the script dir on `sys.path`, and a `test_<script>.py`.
Write/extend them in the same change that adds or edits the script; a script with no test is
incomplete. For a hyphenated (non-importable) hook module, load it in `conftest.py` via
`importlib.util.spec_from_file_location` and alias it in `sys.modules` - for `hooks/`, that means
adding the stem to the `_HOOK_MODULES` map in `hooks/tests/conftest.py`, or the test cannot import
the module and collection fails.

**Run them with CI's dependency set, never a bare `pytest`.** The list lives in
`.github/workflows/ci.yml`: `pytest PyYAML lxml defusedxml ruamel.yaml httpx2`. Anything less
produces failures that read exactly like real defects but are artifacts of the environment:

- without `lxml`, `validate_xml()` returns `(None, None)` instead of `(True, None)`, failing 4 tests
  in `test_validate_structured_files.py`;
- without `httpx2`, `test_proxy_pool.py` fails at COLLECTION, which aborts the whole run;
- `repo-gate.py --ci` shells out to pytest itself, so it needs the same set or it reports
  `repo-gate: FAILED` for a repo that is fine.

```bash
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q
```

Before believing any failure here, check the dependency set first, then confirm it is pre-existing
by stashing your change and re-running.
