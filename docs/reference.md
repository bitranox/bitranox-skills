# Reference

This chapter answers: every knob, file, environment variable, and command the plugin reacts to,
plus the quirks worth knowing. Everything here is current shipped behavior; the chapters before
it explain when and why to use these.

Paths below use `<plugin>` for the installed plugin root
(`~/.claude/plugins/cache/bitranox-skills/bitranox/<version>`). In a session you normally ask
Claude ("view my memory settings", "dream nap") rather than run these by hand - Claude resolves
the paths itself.

## Config knobs

All knobs live in one machine-local file, `~/.claude/.bitranox-memory.json`, managed via
`/bitranox:meta-memory-settings` (`settings.py view | set <key> <value> | reset`). Never
hand-edit it; the CLI validates keys and values. Defaults in brackets.

| Key                 | Values                             | What it controls                                                                                                                                                                                                          |
|---------------------|------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dream_mode`        | `propose` [default], `auto`, `off` | propose: consolidation asks before touching version-controlled files. auto: applies without asking. off: no dream nudges, capture-only memory.                                                                            |
| `privacy`           | `open` [default], `walled`         | open: secret/PII scrub only (memory is machine-local). walled: promotion/gathering also stays within one privacy domain.                                                                                                  |
| `promotion`         | `corroborated` [default], `eager`  | corroborated: a model-inferred rule needs corroboration across dreams before reaching the tree top (which loads for every project under it); user-stated rules promote eagerly either way. eager: promote on first sight. |
| `skill_placement`   | `lowest` [default]                 | New skills live at the lowest scope that fits (project extension before user scope); proposing to the public marketplace is always ask-first.                                                                             |
| `nudges`            | `true` [default], `false`          | Session-start nudges (consolidation due, new-project bootstrap).                                                                                                                                                          |
| `track_private`     | `false` [default], `true`          | Git-track the memory (pointer blocks + `.claude-memory/`) on a PRIVATE repo. Public repos always gitignore both, regardless of this knob.                                                                                 |
| `mcp_search`        | `auto` [default], `off`            | auto: if a read-only memory MCP (e.g. `basic-memory`) covers the store, use it to sharpen cross-project recall; the keyword scan stays the base. off: keyword scan only.                                                  |
| `cross_tree_search` | `true` [default], `false`          | May per-prompt recall scan OTHER knowledge trees? `false` walls recall into the current tree; cross-tree knowledge then moves only via explicit paths (`/collect-knowledge`, the crosstree dream).                        |
| `discovery_roots`   | `[]` [default -> `$HOME`]          | Filesystem roots walked to discover knowledge trees and other projects' stores (JSON list or comma-separated). Set when your projects live outside your home directory.                                                   |

## Sentinel files (all under `~/.claude/`)

| File                            | Effect                                                                                                    |
|---------------------------------|-----------------------------------------------------------------------------------------------------------|
| `.bitranox-memory.json`         | The config above; once it exists it is authoritative                                                      |
| `.bitranox-dream-off` / `-auto` | Pre-config dream-mode switches; honored only until the config file exists (the first write migrates them) |
| `.bitranox-no-autoupdate-nudge` | Dismiss the auto-update reminder without enabling auto-update                                             |

## Environment variables

Set these in the shell that LAUNCHES Claude Code - hooks inherit the session's environment, and a
`/reload-plugins` keeps it.

| Variable                       | Effect                                                                                                                                             |
|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `BITRANOX_HOOKS_OFF=1`         | Dev kill-switch: silences every plugin hook (each prints a one-line skip notice to stderr). Strip per-command with `env -u BITRANOX_HOOKS_OFF ...` |
| `BITRANOX_SKILL_WRITER=1`      | Declares a skill-authoring session: the skill-edit guard admits `SKILL.md` writes                                                                  |
| `BITRANOX_MEMORY_ENGINE=1`     | Declares a store-maintenance session: the store-edit guard admits direct store writes                                                              |
| `BITRANOX_RUN_PYTHON_STRICT=1` | The launcher shim fails loud (exit 3) instead of skipping silently when no Python is found - for deliberate callers, not hooks                     |

## Command-line surface

**The memory engine** - `python3 <plugin>/hooks/memory_engine.py <subcommand>` - is the single
write path to the store. Fail-loud: success prints an explicit line, refusals print
`! refused: ...` and exit non-zero.

| Subcommand                                                                                                                               | Success line                                 |
|------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| `add --proj <cwd> --title T --hook H [--type feedback\|project\|reference\|user] [--body\|--body-file] [--source ..] [--pin] [--slug s]` | the fact's slug                              |
| `move --slug s --from-level <dir> --to-level <dir> [--force]`                                                                            | `moved <slug>: <from> -> <to> (<direction>)` |
| `heal --proj <cwd>`                                                                                                                      | `healed N file(s) across M level(s)`         |
| `set-scope --proj <level> --scope "..."`                                                                                                 | `scope updated: <file>`                      |
| `ensure-memory-structure --proj <cwd>`                                                                                                   | `created N file(s) up the chain`             |
| `tree-top --proj <dir> [--json]`                                                                                                         | `top: ...` / `store: ...`                    |
| `ensure-all-trees [--apply]`                                                                                                             | per-tree report (dry-run without `--apply`)  |

`add` upserts: the same `--slug` updates the fact in place (provenance merged, pin kept). It also
lints the hook - a warning appears when the hook exceeds the soft length cap or has no trigger
phrase ("lead with WHEN it applies").

**Consistency audit**:
`python3 <plugin>/skills/meta-self-improve/reconcile_memory_index.py --check <dirs...>` (a level
dir or an altitude chain) - must end `TOTAL problems: 0`; consolidations verify with it.

**Dream scheduling**: `python3 <plugin>/skills/meta-dream-tree/dream_state.py due|done|mode [cwd]` -
query whether a consolidation is due, mark one done, or print the effective dream mode.

**Generated artifacts** (contributors): `python3 <plugin>/hooks/build_skill_triggers.py` rebuilds
the router map, `python3 <plugin>/hooks/build_skill_docs.py` rebuilds the
[skill catalog](skills.md); both support `--check` and are enforced by pytest sync tests.

## Demo commands

```text
/bitranox:meta-memory-settings        view or change the knobs
/dream-nap                            quick consolidation of the current chain
/dream-tree                           full consolidation of this knowledge tree
/dream-crosstree                      the occasional cross-tree pass
/collect-knowledge                    gather relevant knowledge from other projects
"remember: always X"                  capture a rule on the spot (Stop gate + meta-self-improve)
"pin that rule"                       make a captured rule a binding iron rule
```

## Quirks

- **Update vs reload**: `/plugin marketplace update` serves NEW sessions; a running session keeps
  its version until `/reload-plugins`. Details in [installation.md](installation.md).
- **Windows without Git Bash**: hooks are skipped silently (never an error); skills still work
  when invoked. Details in [installation.md](installation.md).
- **Guards judge the command they see**: a PreToolUse guard evaluates repo state when a command
  is submitted. A compound command that prepares state AND commits in one line is judged on the
  pre-command state - run the preparation as its own command first.
- **Skill authoring is gated twice**: `SKILL.md` writes need the authoring session
  (`BITRANOX_SKILL_WRITER=1`) and a fresh skill-writer receipt (issued by
  `bitranox:meta-skill-writer`, 8-hour TTL); in this repo the repo gate additionally requires the
  committed checklist artifacts. See [CONTRIBUTING.md](../CONTRIBUTING.md).
- **Description changes regenerate two artifacts**: the router map and the skill catalog are
  derived from skill descriptions; sync tests fail the suite until both are rebuilt.
- **Recall noise filtering is learned per project**: a word judged conversational filler in one
  project never suppresses recall in another.
