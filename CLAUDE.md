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
