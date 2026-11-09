# skill-writer checklist - coding-input-sanitization (2026-11-09, data-architecture skill rename)

The Python data-architecture skill is renamed from `coding-python-enforce-data-architecture-strict`
to `coding-python-data-architecture` with no alias, and a generic `coding-data-architecture` is
added. This skill's pointer at the old name is re-pointed.

Decisions: none - a cross-reference follows a rename; no rule of this skill changed.

- [x] Receipt fresh, `bitranox:meta-skill-writer` loaded; `skill_decisions.py show coding-input-sanitization --kind rejected,removed --full` read before the edit (no entry concerns this pointer).
- [x] The change is a pointer only: the target skill exists under the new name (`plugins/bitranox/skills/coding-python-data-architecture/SKILL.md`), and its text holds the worked example or rule the pointer promises (the rich-click facade, the define-the-types section, the end-to-end discipline).
- [x] No behavioural probe: the sentence the reader acts on is unchanged apart from the skill name, so a RED arm has nothing to fail on; the evidence is the text check below.
- [x] Text check: `grep -rn coding-python-enforce-data-architecture-strict` over this SKILL.md finds nothing; `test_no_live_file_names_a_retired_skill` passes.
- [x] The frontmatter description changed (the "see" clause now names coding-python-clean-architecture, coding-data-architecture and coding-python-data-architecture), so `build_skill_triggers.py` was re-run in the same change; the description is 549 characters measured with `len()`, starts "Use when" and keeps every earlier keyword. Routing is a text check only: a live routing answer cannot be taken where the old name is installed.
- [x] See-also: the body line under "Language notes" now names `bitranox:coding-data-architecture` (any language) beside `bitranox:coding-python-data-architecture` (Python).
- [x] ASCII only; no line added over 100 columns except where an existing long paragraph line was edited in place.
