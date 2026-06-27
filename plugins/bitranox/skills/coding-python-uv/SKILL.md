---
name: coding-python-uv
description: >
  Use when writing, configuring, debugging, or deploying Python projects that use
  uv as the package manager, virtual environment manager, Python version manager,
  or pip replacement. Covers project setup, dependency management, lockfiles,
  scripts, tools, building, publishing, Docker, CI/CD, authentication, caching,
  and migration from pip/pip-tools. This covers Version 0.10.2 of uv 2026-02-12
---

# uv - Python Package & Project Manager

All documentation files are flat, numbered markdown files. Use the Read tool to load referenced files identified as relevant for full details.

---

## Command-to-Document Quick Reference

| Command                                          | What it does                                               | Primary doc                     | Also see                        |
|--------------------------------------------------|------------------------------------------------------------|---------------------------------|---------------------------------|
| `uv init`                                        | Create a new project                                       | `02-projects.md`                |                                 |
| `uv add` / `uv remove`                           | Add/remove dependencies                                    | `04-dependencies.md`            | `05-resolution.md`              |
| `uv sync`                                        | Sync environment to lockfile                               | `02-projects.md`                | `04-dependencies.md`            |
| `uv lock`                                        | Update the lockfile                                        | `04-dependencies.md`            | `05-resolution.md`              |
| `uv run`                                         | Run a command in the project env                           | `02-projects.md`                | `07-tools-and-scripts.md`       |
| `uv build`                                       | Build sdist/wheel                                          | `08-building-and-publishing.md` |                                 |
| `uv publish`                                     | Publish to PyPI                                            | `08-building-and-publishing.md` | `11-authentication.md`          |
| `uv export`                                      | Export lockfile (requirements.txt, pylock.toml, CycloneDX) | `04-dependencies.md`            | `09-pip-interface.md`           |
| `uv python install`                              | Install Python versions                                    | `06-python-versions.md`         |                                 |
| `uv python list`                                 | List available/installed Pythons                           | `06-python-versions.md`         |                                 |
| `uv python pin`                                  | Pin Python version for project                             | `06-python-versions.md`         | `10-configuration.md`           |
| `uv python find`                                 | Find a Python interpreter                                  | `06-python-versions.md`         |                                 |
| `uv tool run` / `uvx`                            | Run a tool in isolation                                    | `07-tools-and-scripts.md`       |                                 |
| `uv tool install`                                | Install a tool globally                                    | `07-tools-and-scripts.md`       |                                 |
| `uv tool list`                                   | List installed tools                                       | `07-tools-and-scripts.md`       |                                 |
| `uv venv`                                        | Create a virtual environment                               | `09-pip-interface.md`           |                                 |
| `uv pip install`                                 | Install packages (pip compat)                              | `09-pip-interface.md`           |                                 |
| `uv pip compile`                                 | Lock requirements (pip compat)                             | `09-pip-interface.md`           | `05-resolution.md`              |
| `uv pip sync`                                    | Sync env to requirements.txt                               | `09-pip-interface.md`           |                                 |
| `uv pip uninstall`                               | Remove packages (pip compat)                               | `09-pip-interface.md`           |                                 |
| `uv pip freeze`                                  | Output installed packages                                  | `09-pip-interface.md`           |                                 |
| `uv pip list`                                    | List installed packages                                    | `09-pip-interface.md`           |                                 |
| `uv pip show`                                    | Show package details                                       | `09-pip-interface.md`           |                                 |
| `uv pip tree`                                    | Show dependency tree                                       | `09-pip-interface.md`           |                                 |
| `uv pip check`                                   | Verify env consistency                                     | `09-pip-interface.md`           |                                 |
| `uv cache clean`                                 | Clear cache                                                | `10-configuration.md`           |                                 |
| `uv cache prune`                                 | Remove unused cache entries                                | `10-configuration.md`           |                                 |
| `uv version`                                     | View/bump project version                                  | `02-projects.md`                | `08-building-and-publishing.md` |
| `uv tree`                                        | Show project dependency tree                               | `02-projects.md`                |                                 |
| `uv auth login` / `uv auth logout`               | Manage index credentials                                   | `11-authentication.md`          |                                 |
| `uv auth token`                                  | Print stored auth token                                    | `11-authentication.md`          |                                 |
| `uv python uninstall`                            | Remove managed Python versions                             | `06-python-versions.md`         |                                 |
| `uv python upgrade`                              | Upgrade Python patch version                               | `06-python-versions.md`         |                                 |
| `uv tool upgrade`                                | Upgrade installed tools                                    | `07-tools-and-scripts.md`       |                                 |
| `uv tool uninstall`                              | Remove an installed tool                                   | `07-tools-and-scripts.md`       |                                 |
| `uv tool update-shell`                           | Update shell PATH for tools                                | `07-tools-and-scripts.md`       |                                 |
| `uv cache dir` / `uv tool dir` / `uv python dir` | Show storage directories                                   | `01-getting-started.md`         | `10-configuration.md`           |
| `uv self update`                                 | Update uv itself                                           | `01-getting-started.md`         |                                 |
| `uv self version`                                | Show uv's own version                                      | `01-getting-started.md`         |                                 |

---

## Document Index

| #  | File                            | Contents                                                                                                                                                                                                                                                                                                                                                                                                                   |
|----|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 01 | `01-getting-started.md`         | Feature overview, installation methods (standalone, pip, pipx, Homebrew, Conda, Docker, etc.), shell completion, self-update, uninstallation, installer env vars (`UV_INSTALL_DIR`, `UV_NO_MODIFY_PATH`), first-steps tutorial, getting help                                                                                                                                                                               |
| 02 | `02-projects.md`                | Project creation (`uv init`), templates (`--app`, `--lib`, `--package`), project layout (flat vs src), running commands (`uv run`, `--with`, `--no-project`), syncing environments (`uv sync`, `--frozen`, `--locked`, `--group`, `--only-group`, `--inexact`), `uv version` (view/bump), `uv tree`                                                                                                                        |
| 03 | `03-project-config.md`          | `[project]` table (name, version, requires-python, scripts, entry-points, gui-scripts), `[tool.uv]` settings (dev-dependencies, managed, package, python-preference, default-groups, environments), build systems, project packaging                                                                                                                                                                                       |
| 04 | `04-dependencies.md`            | `uv add`/`uv remove`, dependency groups (`--group dev`), optional deps (`--optional`), platform-specific deps, source deps (git, path, URL, editable, workspace), `uv lock`, constraints (`[tool.uv.constraint-dependencies]`), `uv export` to requirements.txt/pylock.toml/CycloneDX (`--no-hashes`, `--group`, `--all-groups`, `--format`)                                                                               |
| 05 | `05-resolution.md`              | Resolution strategies (`--resolution lowest/lowest-direct/highest`), pre-release handling (`--prerelease`), dependency overrides (`[tool.uv.override-dependencies]`), constraints, `--exclude-newer` / `UV_EXCLUDE_NEWER`, platform-specific resolution, reproducibility, forking resolver                                                                                                                                 |
| 06 | `06-python-versions.md`         | `uv python install/list/find/pin`, version request syntax, discovery order, `.python-version`/`.python-versions` files, `python-downloads` setting, `UV_PYTHON`, `UV_PYTHON_PREFERENCE`, `requires-python`, PyPy support                                                                                                                                                                                                   |
| 07 | `07-tools-and-scripts.md`       | **Tools:** `uv tool run`/`uvx`, `--from`, `--with`, version requests, `uv tool install/list/upgrade/uninstall/update-shell/dir`, tool directories and PATH. **Scripts:** `uv run script.py`, PEP 723 inline metadata (`# /// script`), `uv init --script`, `uv add --script`, shebangs                                                                                                                                     |
| 08 | `08-building-and-publishing.md` | `uv build` (sdists, wheels, `--sdist`, `--wheel`, `--out-dir`, `--package`), uv's build backend (`uv_build`), `[build-system]` config, `[tool.uv.build-backend]` settings, `uv publish`, trusted publishers (PyPI/GitHub OIDC), token auth, `--publish-url`                                                                                                                                                                |
| 09 | `09-pip-interface.md`           | `uv venv` (creating envs, `--python`, `--system`), `uv pip install/uninstall` (PyPI, git, URLs, `--system`, `--target`, `--prefix`, editable), `uv pip compile/sync` (pip-tools workflow), `uv pip show/list/tree/check/freeze`, dependency formats (requirements.txt, pyproject.toml, setup.py), pip compatibility differences                                                                                            |
| 10 | `10-configuration.md`           | Config files (`pyproject.toml [tool.uv]`, `uv.toml`, `.python-version`), precedence (CLI > env > project > user), package indexes (`--index`, `--default-index`, `[[tool.uv.index]]`, `--index-strategy`, per-package pinning), cache (`uv cache clean/prune`, `UV_CACHE_DIR`, `--no-cache`), preview features (`--preview`, `UV_PREVIEW`), storage locations (`UV_CACHE_DIR`, `UV_TOOL_DIR`, `UV_PYTHON_INSTALL_DIR`)     |
| 11 | `11-authentication.md`          | `uv auth login/logout/token`, HTTP auth (credentials in URLs, `.netrc`, keyring `--keyring-provider`, `UV_INDEX_<NAME>_USERNAME/PASSWORD`), Git auth (SSH, credential helpers, GitHub/GitLab tokens), insecure hosts (`--allow-insecure-host`), TLS/SSL (`--cert`, `SSL_CERT_FILE`, `SSL_CLIENT_CERT`), third-party indexes (Google Artifact Registry, AWS CodeArtifact, Azure Artifacts, Hugging Face, JFrog Artifactory) |
| 12 | `12-workspaces.md`              | Monorepo/multi-package projects: `[tool.uv.workspace]` with `members`/`exclude`, workspace root, path dependencies, shared lockfile, `--package` flag                                                                                                                                                                                                                                                                      |
| 13 | `13-docker.md`                  | Docker integration: multi-stage builds, installing uv (ghcr.io image, pip, copy from stage), `UV_COMPILE_BYTECODE`, `UV_LINK_MODE`, layer caching strategies, non-root users, best practices                                                                                                                                                                                                                               |
| 14 | `14-ci-cd.md`                   | **GitHub Actions:** `setup-uv` action, caching, Python version matrix. **GitLab CI/CD:** configuration examples, caching, Docker pipelines                                                                                                                                                                                                                                                                                 |
| 15 | `15-integrations.md`            | FastAPI, Jupyter, Marimo, pre-commit, PyTorch/CUDA indexes (`--torch-backend`), AWS Lambda (packaging, Docker, layers), alternative indexes (`[[tool.uv.index]]`), dependency bots (Renovate, Dependabot), Coiled (Dask)                                                                                                                                                                                                   |
| 16 | `16-migration.md`               | Migrating from pip + requirements.txt to uv projects: converting requirements, creating pyproject.toml, handling constraints files, replacing pip-tools workflows                                                                                                                                                                                                                                                          |
| 17 | `17-troubleshooting.md`         | Build failures (missing system libs, C compiler, `--no-build-isolation`), reproducible examples for bug reports, supported platforms matrix (Linux, macOS, Windows, musl/glibc, aarch64, x86_64, etc.)                                                                                                                                                                                                                     |

---

## Cross-Reference by Scenario

| Scenario                                                         | Read these docs                                                                                   |
|------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **"Set up a new Python project"**                                | `02-projects.md`, `03-project-config.md`                                                          |
| **"Add a dependency"**                                           | `04-dependencies.md`, `05-resolution.md`                                                          |
| **"Add a dev dependency"**                                       | `04-dependencies.md` (search: dependency groups, `--group dev`)                                   |
| **"Pin Python version"**                                         | `06-python-versions.md`, `10-configuration.md`                                                    |
| **"Use a private package index"**                                | `10-configuration.md`, `11-authentication.md`, `15-integrations.md` (Alternative Indexes section) |
| **"Docker build with uv"**                                       | `13-docker.md`, `01-getting-started.md`                                                           |
| **"GitHub Actions CI"**                                          | `14-ci-cd.md`                                                                                     |
| **"GitLab CI"**                                                  | `14-ci-cd.md`                                                                                     |
| **"Deploy to AWS Lambda"**                                       | `15-integrations.md` (AWS Lambda section), `04-dependencies.md`                                   |
| **"Migrate from pip/requirements.txt"**                          | `16-migration.md`, `09-pip-interface.md`                                                          |
| **"Use pip-tools workflow (compile/sync)"**                      | `09-pip-interface.md`                                                                             |
| **"Monorepo / workspace"**                                       | `12-workspaces.md`, `04-dependencies.md`                                                          |
| **"Run a one-off tool (like ruff, black)"**                      | `07-tools-and-scripts.md` (Tools section)                                                         |
| **"Run a script with inline deps"**                              | `07-tools-and-scripts.md` (Scripts section)                                                       |
| **"Build and publish a package"**                                | `08-building-and-publishing.md`, `11-authentication.md`                                           |
| **"Configure resolution (pre-releases, overrides)"**             | `05-resolution.md`, `04-dependencies.md`                                                          |
| **"Use PyTorch / CUDA indexes"**                                 | `15-integrations.md` (PyTorch section), `10-configuration.md`                                     |
| **"Jupyter notebook with uv"**                                   | `15-integrations.md` (Jupyter section)                                                            |
| **"FastAPI project"**                                            | `15-integrations.md` (FastAPI section), `02-projects.md`                                          |
| **"SSL/TLS certificate issues"**                                 | `11-authentication.md`, `17-troubleshooting.md`                                                   |
| **"Build failures / missing C libs"**                            | `17-troubleshooting.md`, `10-configuration.md`                                                    |
| **"Cache problems / disk space"**                                | `10-configuration.md` (Cache and Storage sections)                                                |
| **"Lock reproducibility / --exclude-newer"**                     | `05-resolution.md`, `02-projects.md`                                                              |
| **"pre-commit hooks"**                                           | `15-integrations.md` (pre-commit section)                                                         |
| **"Dependency update bots"**                                     | `15-integrations.md` (Dependency Bots section)                                                    |
| **"Export lockfile (requirements.txt, pylock.toml, CycloneDX)"** | `04-dependencies.md` (Export section), `09-pip-interface.md`                                      |
| **"Editable installs"**                                          | `09-pip-interface.md`, `04-dependencies.md`                                                       |
| **"Using system Python / --system"**                             | `09-pip-interface.md`, `06-python-versions.md`                                                    |
| **"View or bump project version"**                               | `02-projects.md`, `08-building-and-publishing.md`                                                 |
| **"Manage index credentials (login/logout)"**                    | `11-authentication.md`                                                                            |
| **"Export SBOM (CycloneDX)"**                                    | `04-dependencies.md` (Export section)                                                             |
| **"Marimo notebooks with uv"**                                   | `15-integrations.md` (Marimo section)                                                             |
| **"Hugging Face model index"**                                   | `11-authentication.md`, `15-integrations.md`                                                      |
| **"Build isolation issues (flash-attn, deepspeed)"**             | `03-project-config.md`, `17-troubleshooting.md`                                                   |

---

## Key Environment Variables

| Variable                   | Purpose                           | Doc                     |
|----------------------------|-----------------------------------|-------------------------|
| `UV_CACHE_DIR`             | Override cache directory          | `10-configuration.md`   |
| `UV_TOOL_DIR`              | Override tool install directory   | `10-configuration.md`   |
| `UV_PYTHON_INSTALL_DIR`    | Override managed Python directory | `10-configuration.md`   |
| `UV_PYTHON`                | Override Python interpreter       | `06-python-versions.md` |
| `UV_PYTHON_PREFERENCE`     | Prefer managed vs system Python   | `06-python-versions.md` |
| `UV_SYSTEM_PYTHON`         | Use system Python by default      | `14-ci-cd.md`           |
| `UV_PREVIEW`               | Enable preview features           | `10-configuration.md`   |
| `UV_EXCLUDE_NEWER`         | Exclude packages after date       | `05-resolution.md`      |
| `UV_INDEX_<NAME>_USERNAME` | Index auth username               | `11-authentication.md`  |
| `UV_INDEX_<NAME>_PASSWORD` | Index auth password/token         | `11-authentication.md`  |
| `UV_INSTALL_DIR`           | Override uv install location      | `01-getting-started.md` |
| `UV_COMPILE_BYTECODE`      | Compile .pyc during install       | `13-docker.md`          |
| `UV_LINK_MODE`             | Install link mode (copy/hardlink) | `13-docker.md`          |
| `SSL_CERT_FILE`            | Custom CA certificate bundle      | `11-authentication.md`  |
| `SSL_CLIENT_CERT`          | Client TLS certificate            | `11-authentication.md`  |

---

## Key Configuration Snippets

### pyproject.toml `[tool.uv]` settings

Full details: `03-project-config.md`, `10-configuration.md`

```toml
[tool.uv]
dev-dependencies = ["pytest>=8.0", "ruff>=0.5"]
python-preference = "managed"       # prefer uv-managed Python
package = false                     # treat as non-package (app)
default-groups = ["dev"]            # groups installed by default

[[tool.uv.index]]
name = "custom"
url = "https://custom.pypi.org/simple"
explicit = true                     # only use for packages that request it

[tool.uv.sources]
my-pkg = { git = "https://github.com/org/repo", tag = "v1.0" }
```

### Workspace configuration

Full details: `12-workspaces.md`

```toml
[tool.uv.workspace]
members = ["packages/*"]
exclude = ["packages/experimental"]
```

### Dependency overrides and constraints

Full details: `05-resolution.md`, `04-dependencies.md`

```toml
[tool.uv]
override-dependencies = ["package==1.0.0"]
constraint-dependencies = ["package>=1.0,<2.0"]
```

### Index configuration with authentication

Full details: `10-configuration.md`, `11-authentication.md`

```toml
[[tool.uv.index]]
name = "private"
url = "https://private.pypi.org/simple"
```
```bash
export UV_INDEX_PRIVATE_USERNAME=user
export UV_INDEX_PRIVATE_PASSWORD=token
```

---

## Instructions for the Agent

1. **Identify the topic** from the user's question using the Command Reference or Cross-Reference tables above.
2. **Read the primary doc** listed for that topic. All files are at `./<filename>` relative to this SKILL.md.
3. **Read secondary docs** from the "Also see" column or Cross-Reference table if the primary doc doesn't fully answer the question.
4. Each file is self-contained per topic - you typically need only 1-2 files per question.
5. When generating `pyproject.toml` configuration, cross-check with `03-project-config.md` and `10-configuration.md`.
6. When suggesting commands, verify flags and options against the relevant doc before recommending them.
7. For integration-specific questions (FastAPI, Jupyter, PyTorch, etc.), check `15-integrations.md` first - each integration has its own `##` section.
