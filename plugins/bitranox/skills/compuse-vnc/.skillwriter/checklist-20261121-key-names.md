# Review checklist - the key row points at key --help for the full name list (2026-11-21)

Change: the `key` row read "Press one named key: `enter`, `tab`, `esc`, arrows, `f1`-`f12`, ...";
it now ends "`key --help` lists them all". The sentence above the table now also says a command's
`--help` (`vnc-remote-control key --help`) runs without `--port`. Frontmatter unchanged. The CLI
change that makes `key --help` list the names (a help footer built from `keymap.NAMED_KEYS`) ships
in the same release.

## PLAN
- [x] Skill type: reference. Test: a text check of the pre-edit row against the CLI (RED) and a
      retrieval probe with quote-back on the edited section (GREEN).
- [x] Ledger read (`skill_decisions.py show compuse-vnc`, also `--kind rejected,removed --full`):
      nothing rejected or removed; the live `port-scope` rule is extended, not contradicted.
- Decisions: d-20261121-daa0a2cd

## RED
- [x] Text check: the pre-edit row ends in "...", and nothing else gave the full list: `key --help`
      printed only "Press a single named key such as enter, tab, or esc." (measured 2026-11-21,
      before the CLI change). 29 names exist in `NAMED_KEYS`; the row covered 19 (counting the four
      arrows and f1-f12), and a reader needing one of the other 10 (`pageup`, `pagedown`,
      `home`, `end`, `delete`, `backspace`, `space`, ...) had nowhere to look.

## GREEN
- [x] Probe 1, haiku, row edit only: Q1 (find the Page Down name) quoted "`key --help` lists them
      all"; Q2 (does that need `--port`) read the table rule literally as YES - a real gap the
      edit created. Fixed by naming `--help` in the sentence above the table.
- [x] Probe 2, haiku, after the fix: Q1 quoted the row; Q2 answered NO quoting "Its `--help`
      (`vnc-remote-control key --help`) and the CLI's other commands ... run without it."
      Measured: `key --help` and `screenshot --help` exit 0 with no `--port`.

## REFACTOR
- [x] GREEN against RED: the partial example list stays; only "..." was replaced by the pointer.
- [x] Skill gaps reported, each decided:
  - Exact Page Down spelling and the arrow names not in the skill: declined by design; the list
    lives in `key --help`, generated from the keymap, so it cannot drift as a copy here would.
  - Where `--port` goes: declined, an excerpt artifact; the examples right under the table show
    `vnc-remote-control --port 5901 screenshot ...`.
  - What happens without `--port`: declined, out of scope for this edit (a usage error).
  - Authentication: declined, an excerpt artifact; the skill's Authentication section covers it.
  - Case sensitivity: declined here; `key --help` itself says "Case does not matter".
- [x] Mirror: same text in bitranox-skills `plugins/bitranox/skills/compuse-vnc/SKILL.md`;
      `repo-gate.py --mirrors` reports compuse-vnc in sync.
