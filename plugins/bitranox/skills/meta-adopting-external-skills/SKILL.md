---
name: meta-adopting-external-skills
description: Use when importing, adopting, forking, or integrating a useful third-party Claude Code skill into the bitranox marketplace - given a repo URL, an installed plugin path, or a pasted SKILL.md - or when asked to bring an external skill up to bitranox standards. The adopted skill is added alongside the user's other installed plugins, never replacing them.
---

# Adopting External Skills

Take a useful-but-imperfect third-party skill, raise it to bitranox standards, and ship it from
this marketplace so every install benefits. The skill stays correct legally and never disturbs
the user's other plugins.

**Core principle: upstream-first and coexist.** Improve the skill, push the improvement back to
its original author first, and keep a bitranox copy only if upstream stalls or rejects it. The
bitranox copy lives beside the user's other plugins; you never uninstall or disable anything.

## When to use

User-directed only. The user points you at a specific external skill: a repo URL, a path to an
installed plugin/skill directory, or a pasted `SKILL.md`. Do not go hunting for candidates and
do not scan installed marketplaces.

Not for skills you write from scratch (use `bitranox:meta-skill-writer`) and not for a skill that
lives only in a project's own `.claude/skills/` (that stays in that project).

## Iron rules

- **License gate is blocking.** No adoption work begins until the upstream license is verified
  as redistributable and MIT-compatible. No exceptions.
- **Never touch the user's other plugins.** Do not run `/plugin uninstall`, edit
  `~/.claude/settings.json`, or modify any installed-plugin directory. Adoption only ever adds a
  skill to this repo.
- **Upstream-first.** The bitranox copy is the fallback, not the default. Try to fix it at the
  source before you keep a fork.

## Step 1 - License gate (blocking)

> Tiering: offload the bounded analysis of a large external repo to a **`sonnet`** subagent (summarize
> behavior, surface license evidence, list naming/cross-reference normalization deltas) so the whole
> third-party tree stays out of your context; the license accept/reject mapping is mechanical
> (**`haiku`**). The no-license-found path stays a user decision. Tiers: "Concrete tiers" in
> `bitranox:process-agents-subagent-driven-development`.

Find the license. Look beyond the skill's own folder: the source repo root (`LICENSE`/`COPYING`),
SPDX headers, the `license` field of any `plugin.json` / `package.json` / `pyproject.toml` /
marketplace manifest, and a README license section.

- **Accept** the permissive family: MIT, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0. Capture
  the upstream copyright line verbatim and the full license text. For **Apache-2.0** also capture
  any upstream `NOTICE` file and record that you modified the files (Apache-2.0 requires stating
  changes; adoption always modifies).
- **Reject** copyleft (GPL, LGPL, AGPL) and proprietary/all-rights-reserved licenses: they cannot
  be redistributed inside this MIT collection. Stop.
- **No license found anywhere** means all rights reserved, not permissive - **never assume MIT**.
  Stop the mechanical work, research online (the source repo's detected license, the author's
  other repos or registry entries, any stated terms), present what you find, and ask the user for
  a per-case decision. Adopt only on an explicit yes.

## Step 2 - Adopt and normalize (mechanical)

Run the helper:

```
python3 plugins/bitranox/skills/meta-adopting-external-skills/adopt_skill.py <source> [--name <bitranox-name>] [--dest plugins/bitranox/skills]
```

It fetches the source (a shallow clone for a URL, a copy for a local path), runs the license gate
first and aborts if it fails, normalizes the name to bitranox conventions, rewrites the skill's
internal cross-references to `bitranox:<name>`, scaffolds a `tests/` stub when the skill ships
`.py`, records attribution (the credit line plus a `THIRD_PARTY_NOTICES.md` entry), runs the repo
gate read-only, and prints a follow-up checklist. It never commits, never pushes, and never
removes anything. Review every rewrite it reports.

## Step 3 - Enhance to bitranox standards

**REQUIRED: `bitranox:meta-skill-writer`.** Bring the adopted skill up to standard with it -
RED/GREEN/REFACTOR, the description/CSO craft, token budget, cross-platform scripts, and real
tests (replace the scaffolded stub with behaviour tests). Do not duplicate skill-writer here;
follow it.

## Step 4 - Integrate and pass the gate

Per `CONTRIBUTING.md`: the domains list in `bitranox:meta-using-bitranox-skills` is CATEGORIES plus
exemplars, not a per-skill roster (the injected available-skills list is the source of truth for
completeness, and `repo-gate.py` deliberately does not enforce the reverse direction) - so touch it
ONLY if the new skill's prefix is not already covered by a category. Then bump
`plugins/bitranox/.claude-plugin/plugin.json` one MINOR
(a new skill), add a `CHANGELOG.md` entry that describes what the skill does (no provenance
narrative), ship passing tests, and run the gate (`python3 plugins/bitranox/hooks/repo-gate.py
--ci`). Attribution lives in the structured credit line and the `THIRD_PARTY_NOTICES.md` entry,
never as prose history. The helper fills both from a `<name> (upstream)` placeholder; reword the
credit line and the notice `Source:` field to the curated house style (e.g. `the superpowers plugin`;
`Obra Superpowers plugin (URL)`) so a new entry reads like the existing ones.

## Step 5 - Upstream-first and coexist

**REQUIRED: `bitranox:meta-self-improve`, its "Propagating skill (or hook) improvements upstream"
section.** Offer the improvement to the original author first (a PR to their repo). Keep and ship
the bitranox copy only if upstream stalls or declines. Either way the user's other installed
plugins are left untouched - the bitranox copy coexists, and the user chooses which to invoke.

## Common mistakes

- Doing any adoption work before the license check passes.
- Assuming MIT when no license is present (it is all-rights-reserved).
- Letting the helper or yourself commit, push, or uninstall anything.
- Restating skill-writer or self-improve here instead of cross-referencing them.
- Writing provenance narrative ("ported from X") instead of the structured credit line plus the
  notices entry.
- Skipping the index/version/tests gate, so the change ships to no one.
