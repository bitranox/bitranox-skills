---
name: coding-python-new-public-library
description: Use when creating or scaffolding a NEW public bitranox Python library - a pip-installable package with a rich-click CLI, CI across Python 3.9-3.14 on Linux/macOS/Windows, and a PyPI release - or when installing or using a library built from the bitranox_template_py_lib template. Keywords - new library, scaffold, project template, rename-project, bmk, make test, make release, uv pip install.
---

# New public Python library (from the bitranox template)

## Overview

Do not hand-build a new public Python library. Clone the template
`bitranox_template_py_lib` (https://github.com/bitranox/bitranox_template_py_lib),
rename it to your package, and you inherit a working layout, strict typing, a
CLI, and a full CI/test/release pipeline. This skill is the scaffold-install-use
sequence plus the pitfalls that a from-memory guess gets wrong.

## When to use

- Starting any new public bitranox Python library (a reusable package, optionally
  with a registered CLI command).
- Installing or using a library that was built from this template.

Not for: an application/service (use the app template), or a one-off script.

## 1. Scaffold the repo

The rename is driven by the **directory name**, and the shipped scripts do the work.
Name the new directory for your package first, then preview before applying.

```bash
# copy the template into a new dir named for your package (no template history)
git clone --depth 1 https://github.com/bitranox/bitranox_template_py_lib.git lib_wombat
cd lib_wombat
rm -rf .git
git init -b main                 # NEW repos use main, never master
git config core.fileMode false   # softdev mount: manage exec bits explicitly

./rename_dry.sh    # PREVIEW: rename-project --dry-run. Read it, confirm the new
                   # name/paths are "lib_wombat" everywhere before applying.
./rename.sh        # APPLY: rename-project --yes. Takes NO argument - the new name
                   # comes from the directory, not an arg. `./rename.sh lib_wombat`
                   # does nothing with that word.
```

`rename.sh` / `rename_dry.sh` run `rename-project` from
`git+https://github.com/bitranox/rename_project.git` via `uvx`. `reset_git_history.sh`
is the alternative when you cloned WITH history and want to squash it in place instead
of the `rm -rf .git` fresh start above.

## 2. Install

```bash
uv venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"               # editable, with the dev toolchain
```

For installing a FINISHED library (as a user): `uv pip install <name>`, or
`uv tool install <name>` for the CLI, or `uvx <name>` to run without installing.

## 3. Use the result

The template ships a rich-click CLI (two console commands plus `python -m <pkg>`)
and a small library API. Replace the placeholder behaviors with your own.

```bash
<pkg> info      # print resolved package metadata
<pkg> hello     # placeholder success path
<pkg> --help
```

```python
import <pkg> as lib
lib.emit_greeting()     # placeholder; swap for your real API
```

## 4. Develop and release (bmk)

The `Makefile` is a thin bmk wrapper - do not edit it. Trailing args are forwarded;
`make help` lists everything.

```bash
make test                         # lint + pyright + import-linter + bandit + pip-audit + pytest
make push MSG="feat: ..."         # test, commit, push (MSG= is the safe channel)
make bump-patch                   # bump X.Y.(Z+1); also bump-minor / bump-major
make release                      # tag + GitHub release; CI publishes to PyPI
```

CI, the PyPI publish workflow, and CodeQL come from `.github/`, managed by the
`default_cicd_public` template. Never hand-edit `.github/*`. To publish to PyPI, add a
Trusted Publisher on PyPI (owner, repo, workflow `default_release_public.yml`,
environment `pypi`) or set the `PYPI_API_TOKEN` secret.

## If the new repo also ships a skill, it is a marketplace

A repo that ships a Claude Code skill (a `skills/<name>/SKILL.md` plus
`.claude-plugin/plugin.json` and `marketplace.json`) is a plugin marketplace. Two
consequences that a plain library does not have:

- **Protect its default branch on GitHub** (block force-push and deletion, enforce on
  admins). A published marketplace that gets force-pushed silently freezes every install
  (`/plugin marketplace update` is a `git pull` that can no longer fast-forward).
- **Bump the plugin version on every skill change** (`.claude-plugin/plugin.json`,
  semver). Installs only re-fetch on a version change. Keep history append-only; never
  squash or force-push a published marketplace.

## Common mistakes

| Mistake                                            | Fix                                                           |
|----------------------------------------------------|---------------------------------------------------------------|
| `./rename.sh lib_wombat` (passing the name as arg) | Name the DIRECTORY; run `./rename.sh` with no arg.            |
| Skipping `./rename_dry.sh`                         | Always preview first; the dry-run is the safety check.        |
| `git init` on `master`                             | New repos use `main`.                                         |
| Editing `.github/*`                                | Template-managed; change CI in `default_cicd_public` instead. |
| Hand-editing the `Makefile` or version in code     | Makefile is bmk-generated; bump only `pyproject.toml`.        |

## Reference

The template's own docs (in the repo) go deeper:
`docs/installation.md`, `docs/usage.md`, `docs/development.md`,
`docs/systemdesign/module_reference.md`.
