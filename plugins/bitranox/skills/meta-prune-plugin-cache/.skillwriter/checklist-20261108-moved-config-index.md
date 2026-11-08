# skill-writer checklist - meta-prune-plugin-cache (project index under CLAUDE_CONFIG_DIR)

- [x] Change: one sentence saying the project index is `.claude.json` inside the config dir when
      `CLAUDE_CONFIG_DIR` is set; `default_claude_json` and the `--claude-json` help follow it.
- [x] Evidence (measured, CLI 2.1.319): `claude mcp list` with HOME at an empty dir and
      `CLAUDE_CONFIG_DIR` at another empty dir wrote `<config dir>/.claude.json`; the control arm
      without the variable wrote `<home>/.claude.json`. The CLI binary resolves it as
      `join(CLAUDE_CONFIG_DIR || homedir(), ".claude.json")`.
- [x] Decisions: none - `skill_decisions.py show meta-prune-plugin-cache` lists no entries.
- [x] RED (text): `git show HEAD:<SKILL.md> | grep -c 'inside the config dir'` gave 0.
- [x] RED (code): mutation_arm battery, 3 arms (branch removed, override always true, any override
      counts), all KILLED by the four new tests.
- [x] GREEN (quote-back): "Under `CLAUDE_CONFIG_DIR` that index is `.claude.json` inside the config
      dir, which is where Claude Code keeps it then."
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` output names no pair for this skill.
