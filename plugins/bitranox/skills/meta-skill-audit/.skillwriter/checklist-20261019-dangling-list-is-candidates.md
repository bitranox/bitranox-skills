# skill-writer checklist - meta-skill-audit (2026-10-19, a project skill's DANGLING list)

Change: auditing a repo's own `.claude/skills` (`--skills-dir`), a DANGLING finding naming an
installed marketplace skill or a repo path is a candidate: batch-check every target (`test -e` per
repo path, `test -d` per installed skill) before reading any closely, discard the false class in
one pass, and report how many were discarded.

- [x] Skill type: technique - tested by quote-back (verbatim quote, or NONE).
- [x] RED (text as it stood, opus): PARTIAL - a generic "check it yourself" line, no batch check
      and no count of the discarded class.
- [x] GREEN (new text, opus and haiku): answered by a direct quote.
- [x] Claims checked: `--skills-dir` is a real flag (tests/test_audit_cli.py) and the room
      manifest is `REPO_FILES.txt` (scripts/audit_skills.py `REPO_MANIFEST`).
- [x] Skill gaps, declined: picking a version dir when several are cached is the reader's
      environment, not this rule; a missing `REPO_FILES.txt` is the audit script's own error path.
- [x] Lost-result diff: the RED line survives.
- [x] Description unchanged; no table touched.
- [x] Security: no private paths; the cache path uses placeholders.
