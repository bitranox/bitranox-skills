# skill-writer checklist - meta-skill-writer (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.128.0.

- [x] WRONG: the frontmatter section said "Max 1024 characters total", which reads as name plus
      description combined. The vendored Anthropic spec in this same skill states them separately -
      `name` 64, `description` 1024. Both statements (the structure section and the checklist) now
      say per-field.
- [x] DANGLING x3: the library-choice rules referenced a `python-use-modern-libraries` skill. It
      ships as `coding-python-use-modern-libraries`, so all three references now carry the shipped
      name with its `bitranox:` prefix - the skill's own cross-reference rule.
- [x] The two remaining findings concern the vendored `testing-skills-with-subagents.md` and a
      fenced anti-pattern example; recorded as open rather than changed, since one is a deliberate
      illustration of what NOT to do.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every QUOTE checked against the real file; every behavioural claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths added.
