# skill-writer checklist - process-review-enhance-code-quality (2026-11-09, data-architecture skill rename)

The Python data-architecture skill is renamed from `coding-python-enforce-data-architecture-strict`
to `coding-python-data-architecture` with no alias, and a generic `coding-data-architecture` is
added. This skill's pointer at the old name is re-pointed.

Decisions: none - a cross-reference follows a rename; no rule of this skill changed.

- [x] Receipt fresh, `bitranox:meta-skill-writer` loaded; `skill_decisions.py show process-review-enhance-code-quality --kind rejected,removed --full` read before the edit (no entry concerns this pointer).
- [x] The change is a pointer only: the target skill exists under the new name (`plugins/bitranox/skills/coding-python-data-architecture/SKILL.md`), and its text holds the worked example or rule the pointer promises (the rich-click facade, the define-the-types section, the end-to-end discipline).
- [x] No behavioural probe: the sentence the reader acts on is unchanged apart from the skill name, so a RED arm has nothing to fail on; the evidence is the text check below.
- [x] Text check: `grep -rn coding-python-enforce-data-architecture-strict` over this SKILL.md finds nothing; `test_no_live_file_names_a_retired_skill` passes.

- [x] ASCII only; no line added over 100 columns except where an existing long paragraph line was edited in place.
