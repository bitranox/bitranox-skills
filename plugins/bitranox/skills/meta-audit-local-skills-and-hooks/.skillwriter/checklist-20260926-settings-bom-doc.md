# skill-writer checklist - meta-audit-local-skills-and-hooks (2026-09-26, document settings-bom)

`audit_local.py check` reports a settings file that opens with a UTF-8 byte-order mark as
`settings-bom`. The Step 2 list of deterministic checks now names it.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      undocumented check, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the Step 2 check list; no frontmatter change.

## RED
- [x] Old passage pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      the question (which check reports a parseable settings.json that starts with a BOM) answered
      NONE, noting that only `settings-unparseable` is named for settings files.
- [x] Skill gaps asked for: the missing BOM check was the one gap listed.

## GREEN
- [x] New passage pasted, same model and question: answered `settings-bom`, quoting "a settings
      file that opens with a UTF-8 byte-order mark (`settings-bom`".
- [x] GREEN diffed against RED in both directions: nothing a baseline answered correctly was lost.
- [x] Skill gaps asked for again: none reported.
- [x] The stated behaviour checked against `_settings_findings` in `scripts/audit_local.py`,
      including its own wording that whether Claude Code reads through a BOM is not measured.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] No table row changed.
