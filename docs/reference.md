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
hand-edit it; the CLI validates keys and values. Every knob is a USER decision: the defaults are
the recommended state, a choice is recorded once and never re-asked, and `reset` restores all
defaults.

| Key                 | Values                    | Default        | What it controls                                                                                                                                                                                                          | Change it when                                                                                                                                        |
|---------------------|---------------------------|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dream_mode`        | `propose`, `auto`, `off`  | `propose`      | propose: consolidation asks before touching version-controlled files. auto: applies without asking. off: no dream nudges, capture-only memory.                                                                            | `auto` once you have watched a few dreams and trust how they reshape your store; `off` if you want capture-only memory with no consolidation prompts. |
| `privacy`           | `open`, `walled`          | `open`         | open: secret/PII scrub only (memory is machine-local). walled: promotion/gathering also stays within one privacy domain.                                                                                                  | `walled` when separate domains on this machine must not inform each other even in scrubbed form.                                                      |
| `promotion`         | `corroborated`, `eager`   | `corroborated` | corroborated: a model-inferred rule needs corroboration across dreams before reaching the tree top (which loads for every project under it); user-stated rules promote eagerly either way. eager: promote on first sight. | `eager` only if you want fast propagation and accept more noise at the always-loaded tree top (higher blast radius).                                  |
| `skill_placement`   | `lowest`                  | `lowest`       | New skills live at the lowest scope that fits (a repo's own `.claude/skills/` extension before user scope); proposing to the public marketplace is always ask-first.                                                      | Leave it - the knob exists so the placement decision is recorded once instead of re-asked.                                                            |
| `nudges`            | `true`, `false`           | `true`         | Session-start nudges (consolidation due, new-project bootstrap).                                                                                                                                                          | `false` when the session-start reminders are noise for your workflow; consolidation then runs only when you ask.                                      |
| `track_private`     | `false`, `true`           | `false`        | Git-track the memory (pointer blocks + `.claude-memory/`) on a PRIVATE repo. Public repos always gitignore both, regardless of this knob.                                                                                 | `true` only on a private repo where you want the memory versioned and portable with the code.                                                         |
| `mcp_search`        | `auto`, `off`             | `auto`         | auto: if a read-only memory MCP (e.g. `basic-memory`) covers the store, use it to sharpen cross-project recall; the keyword scan stays the base. off: keyword scan only.                                                  | `off` when an installed memory MCP misbehaves or you want the deterministic keyword scan alone.                                                       |
| `cross_tree_search` | `true`, `false`           | `true`         | May per-prompt recall scan OTHER knowledge trees? `false` walls recall into the current tree; cross-tree knowledge then moves only via explicit paths (`/collect-knowledge`, the crosstree dream).                        | `false` when independent trees (say, two clients) must not see each other's notes.                                                                    |
| `discovery_roots`   | JSON list or comma-joined | `[]` (`$HOME`) | Filesystem roots walked to discover knowledge trees and other projects' stores. Empty derives your home directory at runtime.                                                                                             | Your projects live outside your home directory or span several filesystems.                                                                           |

## Sentinel files (all under `~/.claude/`)

Both are absent by default; absent is the normal state.

| File                            | Default | Effect when present                                                           | Who creates it, and when                                                                                                    |
|---------------------------------|---------|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `.bitranox-memory.json`         | absent  | The config above; once it exists it is authoritative                          | The settings CLI, on your first knob change (never created by hand - the CLI validates keys and values)                     |
| `.bitranox-no-autoupdate-nudge` | absent  | Dismisses the session-start auto-update reminder without enabling auto-update | You, by hand (`touch ~/.claude/.bitranox-no-autoupdate-nudge`), when you want the reminder gone but do not want auto-update |

## Environment variables

All four default to UNSET, which is the correct state for normal use - the plugin never sets them
for you, and a regular user never needs any of them. The first three must be in the environment of
the shell that LAUNCHES Claude Code (hook processes inherit the session's environment; exporting
inside a session's Bash command does not reach the hooks, while a `/reload-plugins` keeps the
launch environment).

| Variable                       | Default | Effect when set                                                                                                                                                                   | Who sets it, and when                                                                                                                                                                                            |
|--------------------------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `BITRANOX_HOOKS_OFF=1`         | unset   | Kill-switch: EVERY plugin hook exits immediately (one-line skip notice to stderr). No recall, no router, no capture gate, no nudges - and no guards, so the safety net is off too | Plugin developers only, at session launch, while debugging the hook stack itself. Never for normal use. A dev session re-enables one hook per command with `env -u BITRANOX_HOOKS_OFF bash run-python.sh ...`    |
| `BITRANOX_SKILL_WRITER=1`      | unset   | The skill-edit guard admits `SKILL.md` writes for the whole session                                                                                                               | Skill authors, at session launch, for an extended authoring session. Usually unnecessary: running `bitranox:meta-skill-writer` issues a receipt (8-hour TTL) that admits the edits without the env var           |
| `BITRANOX_MEMORY_ENGINE=1`     | unset   | The store-edit guard admits DIRECT writes to pointer blocks and `.claude-memory/` via file tools                                                                                  | Store maintainers, at session launch, only for deliberate store surgery (migration, manual repair). Normal memory writes go through `memory_engine.py`, which is never blocked - so routine use never needs this |
| `BITRANOX_RUN_PYTHON_STRICT=1` | unset   | The launcher shim fails loud (exit 3) instead of skipping silently when it cannot find a Python interpreter                                                                       | Deliberate callers, per command (e.g. a consolidation invoking the engine), where a silent no-op would fake success. Hooks stay fail-open by design - a hook must never wedge a turn                             |

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
