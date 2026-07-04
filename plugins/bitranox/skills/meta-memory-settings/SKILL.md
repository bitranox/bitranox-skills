---
name: meta-memory-settings
description: Use to view, change, or reset how the bitranox layered memory behaves - on "/memory-settings", "memory settings", "change dream mode", "turn off nudges", "stop promoting to global", "forget less/more", or when the user wants to see or reset these preferences. Reads/writes the one machine-local config the memory hooks and skills obey.
---

# meta-memory-settings

The layered memory has a few habit-dependent choices with no single right answer for everyone. Each
has a recommended default; the user can change any of them, the choice is RECORDED, and it is applied
automatically thereafter (never re-asked). All knobs live in one machine-local file,
`~/.claude/.bitranox-memory.json`; this skill is the front door to it.

## Use the CLI
- **View:** `python3 <this-skill-dir>/settings.py view`
- **Set one knob:** `python3 <this-skill-dir>/settings.py set <key> <value>`
- **Reset all to recommended defaults:** `python3 <this-skill-dir>/settings.py reset`

When the user is deciding, state the option's consequence and the recommendation in one line, set it,
then confirm. Do not edit the JSON by hand - the CLI validates keys and value types.

## The knobs (recommended default in brackets)

| Key                 | Values                             | What it controls / consequence                                                                                                                                                                                                                                                                                                                                                                                                                  |
|---------------------|------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dream_mode`        | `propose` [default], `auto`, `off` | propose: ask before version-controlled CLAUDE.md edits, self-PR skills. auto: apply without asking. off: no nudges, memory-only.                                                                                                                                                                                                                                                                                                                |
| `privacy`           | `open` [default], `walled`         | open: a secret/PII scrub only (memory is machine-local, not committed). walled: also keep promotion/gather within one privacy domain. Consequence: a global rule (at the topmost-CLAUDE.md-ancestor tier) is recalled into EVERY session under that tree, including public repos.                                                                                                                                                               |
| `promotion`         | `corroborated` [default], `eager`  | corroborated: a model-inferred rule needs >= 2 dreams before it reaches the global layer at the topmost-CLAUDE.md ancestor (recalled into every session under that tree); user-stated rules promote eagerly either way. eager: promote inferred rules on first sight (higher blast radius).                                                                                                                                                     |
| `nudges`            | `true` [default], `false`          | session-start nudges (consolidation-due, new-project bootstrap). Switch off if they are noise.                                                                                                                                                                                                                                                                                                                                                  |
| `track_private`     | `false` [default], `true`          | git-track the memory (the `CLAUDE.local.md` pointer block + the anchor's `.claude-memory/` central bodies) on a PRIVATE repo (portable/shared memory). Public/default ALWAYS gitignore `CLAUDE.local.md` + `.claude-memory/` (this knob does not override that).                                                                                                                                                                                |
| `mcp_search`        | `auto` [default], `off`            | `auto`: if a memory MCP (e.g. `basic-memory`, correctly configured read-only over the local files) is present, use it as a full-text+graph index to sharpen CROSS-project recall; else fall back to the keyword scan. `off`: keyword scan only.                                                                                                                                                                                                 |
| `cross_tree_search` | `true` [default], `false`          | may the per-prompt recall hook scan OTHER knowledge trees (machine-global over `discovery_roots`)? `false` walls recall into the CURRENT tree (its own projects + tree top only; the machine-local native tier counts as outside); cross-tree knowledge then moves only via the explicit paths (`bitranox:meta-collect-knowledge` import, dream-global). Use `false` when independent trees (e.g. two clients) must not see each other's notes. |
| `discovery_roots`   | `[]` [default -> derived]          | extra filesystem roots to walk for other projects' curated stores (each level's `CLAUDE.local.md` pointer block + the anchor's `.claude-memory/` bodies) (JSON list or comma-separated). Empty -> derive `$HOME`. Never ship absolute maintainer paths in the tracked default.                                                                                                                                                                  |

## Notes
- A reset restores every knob to the recommended default above.
- Legacy `~/.claude/.bitranox-dream-off` / `.bitranox-dream-auto` sentinels are honored only until this
  config file exists; the first write migrates the mode into the config (one-way).
