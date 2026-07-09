# skill-writer checklist - coding-python-pwshpy (2026-07-09, mirror of pwshpy repo's using-pwsh)

- [x] Change: new skill, verbatim mirror of the pwshpy repo skill (skills/using-pwsh/SKILL.md); only frontmatter name re-namespaced to the coding-python- category. Body, description, tables identical.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] Review: source SKILL.md read verbatim and diffed against the mirror; only the name line differs
- [x] Discovery test: RED/GREEN subagent campaign run on the source skill in the pwshpy repo (neutral baseline shelled out to pwsh/Get-*; with the skill it used ps.get_service()/pwshpy --jsonl/ps.cmdlet). Verbatim body, so the result carries.
- [x] Security scan: prose/frontmatter/table edits, no secrets/paths/PII
