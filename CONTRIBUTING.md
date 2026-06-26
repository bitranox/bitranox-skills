# Contributing to bitranox-skills

Thanks for improving the collection. Skills here ship as a Claude Code plugin, so the
**installed copy is not where you edit** - read this first.

## Two kinds of self-improvement output

The `self-improve` skill produces two different things. Only one belongs in this repo.

1. **Personal learnings - stay local.** Memory entries and project `CLAUDE.md` guardrails
   are specific to your machine, your infrastructure, and your projects. They live in your
   own `~/.claude/.../memory/` and project files and must NOT be sent here. They often contain
   private hostnames, paths, or corrections.
2. **Skill improvements - come here.** Changes to a skill's `SKILL.md`, its helper scripts, or
   the `self-improve` gate are improvements to the shared artifact and belong in this repo.

## Why you cannot just edit the installed skill

Once installed, the plugin is a managed git clone. `/plugin marketplace update` re-fetches from
this repo and **overwrites** the installed files. Any edit to the installed copy is lost on the
next update. This repo is the single source of truth.

## Versioning (always bump, per semver)

Installed copies only re-fetch when the version changes, so **every change that affects the
distributed plugin (anything under `plugins/bitranox/`) MUST bump
`plugins/bitranox/.claude-plugin/plugin.json`** following semver:

- **MAJOR** - a breaking change to the published surface: removing or renaming a skill, or
  changing a skill's invocation or behaviour in an incompatible way.
- **MINOR** - backward-compatible additions: a new skill, or a new capability in an existing one.
- **PATCH** - backward-compatible fixes: bug fixes, wording/doc fixes inside a skill, test additions.

Note the bump in the commit subject (`...; bump to X.Y.Z`), matching the existing history.
Repo-meta changes outside the plugin tree (this file, the root `README`, CI) do not ship to
installed copies and do not need a plugin bump.

## When you add, rename, or remove a skill

Keep the registry in sync, or the local pre-commit gate and CI (`hooks/repo-gate.py`) will block you:

- **Update `using-bitranox-skills`.** Add the skill to the domains list in
  `plugins/bitranox/skills/using-bitranox-skills/SKILL.md` (and drop or rename stale entries). The
  gate checks both directions: every shipped skill must be listed, and every name listed must exist.
- **Update cross-links.** A rename changes the invocation name (`bitranox:<name>`); fix every
  reference in other skills, hooks, and the README (`grep -rn '<old-name>'`).
- **Bump the version** per semver above (a rename is MAJOR; a new skill is MINOR).
- **Ship tests** for any script the skill bundles (a `tests/` dir with passing pytest) - also gated.

## Authoring craft lives in the `skill-writer` skill

The general craft of writing a skill - description/CSO, structure, flowcharts, token efficiency,
cross-platform scripts, and testing - lives in the shipped `skill-writer` skill. Follow it for any
skill, here or independent. This file is only the **extra** rules specific to contributing to this
marketplace repo (versioning, the registry sync above, the contribution gate, history policy). When
you learn a new authoring rule, put general ones in `skill-writer` and repo-only ones here.

## Security review (required, every commit and PR)

This repo is a PUBLIC marketplace, so anything committed is published. A security scan is part
of the gate (`hooks/repo-gate.py`) and runs on every commit and in CI:

- **Auto-enforced (the gate blocks the commit/PR):** credential formats (GitHub / AWS / Google /
  Slack / GitLab tokens, OpenAI / Anthropic keys), embedded private keys, and sensitive filenames
  (`.env`, `id_rsa`, `*.pem`, `credentials.*`). These never belong in a shipped skill.
- **Maintainer infra denylist (local, optional):** put your own private hostnames, domains, and
  IPs (one per line) in a gitignored `.security-denylist.local` at the repo root (or
  `~/.config/bitranox/security-denylist.txt`). The gate then blocks any commit that reintroduces
  them. The file is gitignored, so the terms are never published.
- **Judgment review (you or an agent, before pushing):** the gate cannot tell a generic example
  IP/domain from a real one. Review the diff for leaked infrastructure, internal IPs/hostnames,
  and personal data. Use documentation-safe placeholders in examples: `example.com` /
  `example.test` for domains and the RFC5737 ranges (`192.0.2.0/24`, `198.51.100.0/24`,
  `203.0.113.0/24`) for IPs.

Catch it BEFORE you push: history here is append-only, so a value that is pushed stays in public
history even after you remove it from the current files (scrubbing needs a force-push, which
breaks every existing install).

## Docs describe the current state only (no legacy noise)

Everything shipped (CHANGELOG, `SKILL.md`, README) is public and read by people who do not know this
repo's internals. Document what a skill does and when to use it, never its provenance or history:

- No "integrated from `<X>` command", no "ported/migrated from `<old>`", no references to private
  commands, files, or internal sources.
- No back-compat or legacy framing for the marketplace itself ("formerly", "old name was", "kept for
  compatibility"). A breaking-rename CHANGELOG note that tells users the NEW invocation name is fine
  (current-state info users need); internal provenance is not.

When you port or integrate a skill, describe the skill, not where it came from.

**Exception: license attribution is required, and is not legacy noise.** When a skill adapts a
third-party skill under a permissive license, copyright law requires crediting the source - that
credit is current-state legal metadata, not provenance narrative. Record it in exactly two places:
(1) a single structured credit line at the top of the skill body, `> Adapted from <source>
(<LICENSE>).`, naming only the source and its license; and (2) a full entry in
`plugins/bitranox/THIRD_PARTY_NOTICES.md` (the upstream copyright line verbatim, the license text,
and - for Apache-2.0 - its `NOTICE` and a "modified" note). Everything else in this section still
holds: no "ported/migrated from", no internal command or file names, no "formerly known as". The
distinction is mechanical - a credit line that names source + license is allowed; prose that
narrates the porting history is not. The `bitranox:adopting-external-skills` skill walks the whole
adoption flow, and `repo-gate.py` keeps the credit lines and notices in sync.

## Contributor workflow (PR)

If your `self-improve` improved a shared skill and you want to share it:

**Preferred: let `self-improve` open the PR.** When self-improve makes a shared-skill change, it
forks this repo (or uses your existing fork), applies the change on a branch, scans it for secrets
and private data, and opens a structured PR for you - gated by a short permission prompt - in the
format below. This is the recommended path: the PR comes out correctly shaped for automated review.

**Manual alternative**, if you would rather do it by hand:

1. Fork this repo.
2. Edit `plugins/bitranox/skills/<skill>/SKILL.md` (or the gate or scripts).
3. Open a PR in the format below.

**Out of scope:** project-specific skills (skills that live in a project's own `.claude/skills/`).
Do not open PRs for them - their improvements stay in that project.

## PR format (for automated review)

Write the PR so an agent can merge or reject it without guessing. Keep the diff minimal and
focused on one skill.

- **Title:** `skill(<skill-name>): <one-line change>` (or `gate:` / `docs:`).
- **Body sections:**
  - **Motivation** - the learning or failure that prompted the change, in one or two sentences.
  - **What changed** - the concrete edit, file by file.
  - **Scope** - confirm this is a shared skill, not project-specific, and that it applies beyond
    your own setup.
  - **Safety** - confirm the diff was scanned and contains no secrets, personal data, or
    infrastructure references.

## Authoring hooks and scripts (cross-platform)

Hooks and helper scripts must run on Windows, macOS, and Linux.

- **Write hook logic in Python, not bash.** Bash tools (`jq`, `cksum`) are not portable. The
  self-improve gate is `hooks/self-improve-gate.py`, pure standard library.
- **Bash is NOT guaranteed on Windows.** Claude Code uses Git Bash only when Git for Windows is
  installed, and falls back to PowerShell otherwise ([setup.md](https://code.claude.com/docs/en/setup.md)).
  An auto-fired hook still needs a shell command in `hooks.json`; we launch the Python gate with
  `bash run-python.sh <gate>.py` (matching Claude Code's own official plugin hooks), where
  `run-python.sh` resolves a working Python 3 (the Windows Store `python3` stub, `py -3`, UTF-8,
  Git Bash `/c/...` paths). That hook fires on macOS/Linux and on Windows-with-Git-Bash; without
  bash it is simply skipped (the gate fail-opens and never errors a turn).
- **Agent-run helpers must be pure Python, never `.sh`.** A script the agent invokes itself (not an
  auto-hook) must be Python, called as `python script.py`, so it runs under PowerShell on Windows
  too. Do not ship `.sh` helpers for cross-platform skills - on native Windows without Git Bash
  they cannot run at all.
- **Mark directly-invoked scripts executable in git.** This repo has `core.fileMode = false`, so
  a working-tree `chmod +x` is NOT recorded and the installed plugin copy ends up non-executable.
  Use `git update-index --chmod=+x <file>`. A script run through an interpreter (`python3 x.py`)
  does not need the bit.
- **Build paths with `pathlib`, never backslashes.** In cross-platform Python, construct paths with
  `pathlib.Path` (or forward slashes) - e.g. `Path(tempfile.gettempdir()) / name` - not a `\` literal.
  pathlib renders the correct separator per OS, and Python reads `/` on every OS including Windows.
- **Where the Stop hook fires:** the Claude Code CLI and the Claude Desktop app's Code tab (same
  engine) - on macOS/Linux always, on Windows only when Git for Windows provides bash. It does NOT
  run in the consumer Claude Desktop Chat or Cowork tabs (no plugins there); on the web app it runs
  in Anthropic's cloud sandbox. Every failure path in the gate exits 0, so a missing shell,
  interpreter, or unsupported surface never wedges a turn.
