# skill-writer checklist - meta-prune-plugin-cache (reload keeps .in_use locks)

- [x] Change (doc only): `/reload-plugins` does not release a session's `.in_use` lock; only the
      process exiting does; the plan's `in use by pid <N>` line names the holder.
- [x] Evidence (read-only, this machine's cache): one live `claude` process held `.in_use` locks on
      four bitranox versions at once (9.1.2, 9.1.3, 9.2.5, 10.4.2), so a process keeps the locks of
      versions it reloaded away from. The "in use by pid" text is quoted from pluginprune.py.
- [x] RED (text): `git show HEAD:<SKILL.md> | grep -c reload-plugins` gave 0.
- [x] GREEN (quote-back): "**`/reload-plugins` does not release a lock; only the process exiting
      does.**"
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
