# skill-writer checklist - meta-audit-local-skills-and-hooks (PEP 723 deps, account sync)

- [x] Change (code, TDD in tests/test_audit_local.py and hooks/tests/test_harness_checks.py):
      test collection retries with the PEP 723 `dependencies` the skill's scripts declare;
      `~/.claude/skills/synced/` is skipped as externally owned and listed under `skipped`.
- [x] RED (text): `git show HEAD:<SKILL.md> | grep -c` gave 0 for "synced" and "PEP 723".
- [x] GREEN (quote-back): ownership table row "`~/.claude/skills/synced/` (the claude.ai account
      skill sync) | owned by the account - REPORT ONLY, fix it in claude.ai"; tests bullet "The
      check reads those `# /// script` blocks and collects WITH their dependencies". Table
      reformatted with reformat_tables.py.
- [x] Real read-only run of `audit_local.py check` on this machine's home: exit 0, synced listed
      under skipped, no synced findings.
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
