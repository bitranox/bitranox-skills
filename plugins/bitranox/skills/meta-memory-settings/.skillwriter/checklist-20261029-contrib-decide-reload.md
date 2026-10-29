# skill-writer checklist - meta-memory-settings (decide needs a reload)

- [x] Change (code, TDD in tests/test_settings.py): `set <site> decide` prints a stderr note that
      open sessions keep the hook they loaded until `/reload-plugins` or a restart.
- [x] RED (text): `git show HEAD:<SKILL.md> | grep -c reload-plugins` gave 0.
- [x] GREEN (quote-back): Notes "Run `/reload-plugins` in each open session (or restart it);
      `set` prints the same reminder to stderr." - matches DECIDE_RELOAD_NOTE in settings.py.
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
