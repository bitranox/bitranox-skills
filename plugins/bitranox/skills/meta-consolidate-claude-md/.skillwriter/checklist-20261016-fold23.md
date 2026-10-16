# skill-writer checklist - meta-consolidate-claude-md (2026-10-16, fold of always-loaded rules)

- [x] Change: "5. Verify the result": new bullet - after a bulk line or bullet delete across many
      files, diff EVERY touched file against its snapshot and read the line at each deletion point,
      because a wrapped bullet's column-0 continuation escapes an indentation-based deleter; flag a
      non-empty, lowercase line that opens no bullet, heading, table, quote or code fence; prove the
      check fires on a known-bad file; repair an orphan by keeping its delta as a clean bullet.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit the skill had no text for orphaned
      column-0 continuations (verifier gap: "Nothing in the skill says that a wrapped bullet's
      continuation can sit at column 0 and escape an indentation-based deleter ... A spot-read of
      one member file would miss the one bad file among 30"). Behavioural RED replaced on purpose
      because the rule is in the always-loaded memory index of the authoring machine (inherited
      coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): column-0
      continuation orphan -> SKILL.md:133-138 "When the trim deleted a line or bullet from many
      files, diff EVERY touched file against its snapshot and read the line now sitting at each
      deletion point: a wrapped bullet's continuation can start at column 0 ... prove the check
      fires on one known-bad file first, and repair an orphan by keeping any delta it carried as
      its own clean bullet."; contradictions: none in job; unlinked md: none in job; step-4 scan
      of the SKILL.md diff: no non-ASCII, no hostnames/paths, no private provenance.
- [x] Gaps closed or declined: none.
- [x] Description measured: unchanged (483 chars)
- [x] The skill's own `tests/` pass after the edit.
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
