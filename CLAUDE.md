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

## A skill that also ships from its own tool repo has a twin to keep in sync

Nine skills exist twice: here, and in the repo of the tool they document (the map is
`MIRRORED_SKILLS` in `hooks/repo-gate.py`; `--mirrors` also reports a twin the map does NOT list,
which is how the ninth was found after going unchecked). Both copies are installed by real users, so drift is
not cosmetic - and it goes both ways. A marketplace edit that is never mirrored back leaves the
tool repo's own installs a release behind; a repo edit that is never mirrored forward leaves this
marketplace describing behaviour the tool no longer has. The second kind is the dangerous one: an
absence claim that has gone stale ("it refuses to do X") does not merely fail to help, it steers an
agent away from something that now works.

Three differences are by convention and are never drift: the `name:` field, that same name echoed
in the H1, and the tool repo's self-install blockquote (true there, nonsense here). Everything else
must match.

- The commit gate checks the twin of any mirrored skill the current change touches. Pre-existing
  drift elsewhere does not block an unrelated commit.
- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` audits all eight, changed or not, and
  exits non-zero when any has drifted. This is local only: the twins are sibling repos that a CI
  clone does not have, so CI cannot run it.
- `repo-gate.py --mirror-of <tool-repo>` asks the same question from the other side, about that one
  repo's pair only. It is what a tool repo's release pipeline runs before pushing, where another
  repo's drift would be no reason to block. Safe to run anywhere: a repo with no mirrored skill, a
  machine with no marketplace checkout, and a path outside the tree all print why and pass.
- To fix drift, regenerate the stale side from the other, re-apply the three divergences, and bump
  THAT repo's `plugin.json` - both copies ship, so both need a version the installer can see.

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

## Enable the pre-push hook once per clone

```bash
git config core.hooksPath githooks
```

`githooks/pre-push` runs `repo-gate.py --pre-push`: the maintainer check set plus the whole-repo
pytest CI runs. Enable it in every clone you push from, because the check that catches a stale
generated artifact is only as good as the moment it fires.

The PreToolUse `repo-gate` already gates `git commit` and `git push`, but it is a Claude Code hook,
so it cannot fire when git runs from a terminal, an IDE, or a script. That blind spot is exactly
one habit wide and a stale `docs/skills.md` shipped through it twice, in 5.166.0 and 5.166.1, each
time missing a skill the README count then contradicted. A git-level hook has the property the
PreToolUse one cannot: git runs it for every push whatever invoked it.

Two things make it silently do nothing, both of which have bitten:

- **A non-executable hook is skipped by git without a word.** `core.fileMode` is `false` in this
  repo, so a working-tree `chmod +x` is not recorded; the index mode is what a fresh clone gets.
  Verify with `git ls-files -s githooks/pre-push` showing `100755`, and note that a clone still
  needs its own `chmod +x` only if it turned `core.fileMode` off before checkout.
- **An inherited `VIRTUAL_ENV` picks the wrong interpreter**, which is how the gate once reported
  the CI dependencies missing while sitting in an unrelated project's venv. The hook unsets it and
  prefers `uv`, taking the dependency list from `repo-gate.py --print-test-deps` so it cannot drift
  from `ci.yml`.

`git push --no-verify` bypasses it for a genuine emergency.
