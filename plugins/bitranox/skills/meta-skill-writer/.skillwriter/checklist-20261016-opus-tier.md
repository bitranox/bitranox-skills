# skill-writer checklist - meta-skill-writer (2026-10-16, opus tier)

- [x] Change: the RED dispatch example pins `opus` and the authoring rule says `opus`, or `haiku` for purely mechanical work (was haiku / sonnet / opus, default fan-out `sonnet`), per "Concrete tiers" in `process-agents-subagent-driven-development`, which drops `sonnet` as a dispatch tier.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED (text check of the artifact): `plugins/bitranox/hooks/tests/test_model_tiers.py`, written
      before the edit, failed listing this skill's `sonnet` tier line(s) among 45 plugin-wide hits.
      A behavioural RED was replaced on purpose: `redcheck.py --corpus-cascade` reported INHERITED
      COVERAGE (STRONG) - the always-loaded memory index on the authoring machine already says
      "never sonnet", so a behavioural arm answers `opus` with or without this text.
- [x] GREEN: the same test passes; no line of this skill names `sonnet` as a tier.
- [x] No other text changed; the frontmatter description is unchanged
- [x] Security scan: prose edits only, no secrets, hostnames, paths or PII
