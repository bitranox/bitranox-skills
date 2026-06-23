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
- **Invoke through the launcher.** Claude Code runs hook commands through bash on every desktop
  platform (Git Bash on Windows), so bash itself is safe; the hard part is finding Python (the
  Windows Microsoft Store `python3` stub, the `py -3` launcher, UTF-8, Git Bash `/c/...` paths).
  So `hooks.json` calls `bash run-python.sh <script>.py`, and `run-python.sh` resolves a working
  Python 3 and execs it.
- **Mark directly-invoked scripts executable in git.** This repo has `core.fileMode = false`, so
  a working-tree `chmod +x` is NOT recorded and the installed plugin copy ends up non-executable.
  Use `git update-index --chmod=+x <file>`. A script run through an interpreter (`python3 x.py`)
  does not need the bit.
- **Build paths with `pathlib`, never backslashes.** In cross-platform Python, construct paths with
  `pathlib.Path` (or forward slashes) - e.g. `Path(tempfile.gettempdir()) / name` - not a `\` literal.
  pathlib renders the correct separator per OS, and Python reads `/` on every OS including Windows.
- **Where the Stop hook fires:** the Claude Code CLI on all OSes, and the Claude Desktop app's
  Code tab (same engine, shared config). It does NOT run in the consumer Claude Desktop Chat or
  Cowork tabs; on the web app it runs in Anthropic's cloud sandbox. Every failure path in the gate
  exits 0, so a missing interpreter or unsupported surface never wedges a turn.
