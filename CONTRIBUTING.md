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
