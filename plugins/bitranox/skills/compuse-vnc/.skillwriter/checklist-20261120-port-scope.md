# Review checklist - --port is needed by the table's commands, not every command (2026-11-20)

Change: the Commands section's first sentence read "Every command needs `--port`". It now reads
"Every command in this table needs `--port`; `--host` defaults to `127.0.0.1`. The CLI's other
commands (`info`, `config`, the email commands) run without it." Frontmatter unchanged.

## PLAN
- [x] Skill type: reference. Test: a text check of the pre-edit file against the CLI (RED) and a
      retrieval probe with quote-back on the edited section (GREEN).
- [x] Ledger read (`skill_decisions.py show compuse-vnc`, also `--kind rejected,removed --full`):
      nothing rejected or removed; the one live rule (VMware Workstation) is unrelated.
- Decisions: d-20261120-ae33b4fc

## RED
- [x] Text check: the pre-edit line "Every command needs `--port`" is unqualified, and the CLI
      contradicts it: `vnc-remote-control info` exits 0 with no `--port` (run 2026-11-20). The six
      table commands all go through `_server()`, which raises a UsageError without `--port`
      (`src/vnc_remote_control/adapters/cli/commands/vnc.py`).
- [x] Route: text check rather than a behavioural arm; the defect is a false sentence, and a
      probe reading it can only repeat it.

## GREEN
- [x] Probe on the edited section, haiku (1 cell; the weakest tier, a literal reader): `info`
      needs no `--port` (quoted "The CLI's other commands (`info`, `config`, the email commands)
      run without it."), `screenshot` does and the host defaults to 127.0.0.1 (quoted "Every
      command in this table needs `--port`; `--host` defaults to `127.0.0.1`.").

## REFACTOR
- [x] GREEN against RED: nothing removed; the sentence was narrowed and one sentence added.
- [x] Skill gaps reported, each decided:
  - What host `info` and `config` use: declined, they open no connection, so no host applies.
  - Whether `--port` has a default: declined, "needs" says it; `_server()` refuses a missing one.
  - "--us-shift: see below": declined, an excerpt artifact; the full skill covers `--us-shift` in
    its Gotchas ("QEMU's own VNC server needs `type --us-shift`").
  - The `key` row ends in an ellipsis and nothing lists every key name (`key --help` does not
    either, checked 2026-11-20): declined here as out of scope for this edit, which touches
    neither the CLI nor the key list; filed in the repo backlog (make `key --help` list the
    names, then point the row at it).
  - "the email commands" not named: declined, they are outside this skill's scope and the CLI's
    `--help` lists them.
- [x] Mirror: same text in bitranox-skills `plugins/bitranox/skills/compuse-vnc/SKILL.md`;
      `repo-gate.py --mirrors` reports compuse-vnc in sync.
