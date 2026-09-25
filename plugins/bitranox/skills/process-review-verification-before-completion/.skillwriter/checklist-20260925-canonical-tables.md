# skill-writer checklist - process-review-verification-before-completion (2026-09-25, tables to canonical form)

Change: 6 table lines are re-padded to the canonical form of
`docs-md-table-formatting/reformat_tables.py`. No cell's text, no alignment, no row and no line
outside a table changes, so the rendered table and every word a reader or router sees are
identical. The file was not in canonical form, so the reformat-md-tables hook rewrote it in every
fresh checkout and the commit gate then demanded a checklist for a skill nobody had edited.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type irrelevant to the change: no teaching content moves. This is NOT the named
      syntax-only front-matter exception; it is the same kind of change (a machine-checkable
      formatting repair with nothing for an agent to get wrong), recorded here with its proof in
      place of a RED/GREEN arm, which would have no behaviour to fail on.
- [x] Scope: table padding only; frontmatter, `name:` and description byte-identical.

## Proof (mechanical, in place of RED/GREEN)

- [x] Line count unchanged; every changed line is a table row on both sides.
- [x] Every cell equal after stripping, split on unescaped `|`; every separator row keeps its
      alignment colons. Checked by a script comparing the pre- and post-format text line by line.
- [x] Control: the same cell comparison reports a changed cell (`| a | b |` against `| a | c |`)
      and a changed alignment (`|:--|--|` against `|--|--|`) as different, and keeps an escaped
      pipe inside its cell, so its "whitespace-only" verdict can fail.
- [x] `reformat_tables.py --check SKILL.md` exits 0 afterwards (canonical).

## Quality

- [x] No address, hostname or machine path added; no link or doc reference changed.
- [x] Security: whitespace only.
