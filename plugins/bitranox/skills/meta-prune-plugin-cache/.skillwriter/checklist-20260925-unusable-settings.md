# skill-writer checklist - meta-prune-plugin-cache (2026-09-25, unusable settings source)

Change: the "Use the tool" section documents what `scripts/pluginprune.py` now does with a
settings source it cannot use. A settings file or `~/.claude.json` that exists but cannot be
read, is not UTF-8, is not valid JSON or has the wrong shape stops the run with exit 2 before
anything is planned or removed, naming the file and the reason; so does a `--settings` or
`--claude-json` naming a missing file. A discovered file that is absent or holds only whitespace
is ordinary. The `--json` example's exit-code comment gains "or unusable settings".

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. Test approach: a retrieval arm, five questions (four the
      change moves, one unchanged control), each answered with a direct quote of the governing
      text or NONE, run on the least inferential tier (haiku) with the inert
      `bitranox:baseline-probe` agent type, the text pasted into the prompt.
- [x] Scope: two edits in the "Use the tool" section; frontmatter, description and `name:`
      unchanged (the diff touches no `---` line).

## RED

- [x] Inherited coverage checked first: `redcheck --corpus-cascade` over the skill dir read 1252
      documents and reported STRONG coverage from two always-loaded CLAUDE.local.md indexes,
      sharing only function words (prune, settings, valid, trailing) with the scenario. Route
      taken either way: the behavioural arm is replaced by a text check of the artifact (the
      quote-back retrieval arm above), which inherited context cannot answer.
- [x] RED, pre-change text: Q1 (settings.json not valid JSON, its enabledPlugins names a sole
      version), Q2 (`--settings` naming a missing file), Q3 (absent settings.local.json) and Q4
      (truncated `~/.claude.json`) all answered NONE. Q5 (missing installed_plugins.json, the
      control) answered exit 1 with the governing quote.
- [x] RED `Skill gaps` recorded: no error handling stated for settings.json, settings.local.json
      or `~/.claude.json` being malformed, missing or unreadable; no tolerance stated for a
      missing member of the user's pair.

## GREEN

- [x] Q1 exit 2, run stops before planning; Q2 exit 2; Q3 not a problem; Q4 exit 2, nothing
      processed - each with a direct quote of the new paragraph (quote-back). Q5 unchanged: exit 1,
      same quote.
- [x] GREEN `Skill gaps`: none reported.
- [x] Diffed against RED in both directions: the one RED answer that was right (Q5) is still right
      with the same quote; nothing the baseline answered was lost.
- [x] The earlier checklist's declined gap "unreadable settings files" is closed by this change.

## Quality

- [x] Frontmatter untouched; `name` and `description` byte-identical, so no trigger moved.
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Word count 1252; the added paragraph carries an exit code and a remedy a reader acts on, and
      the tool's module docstring and `--help` epilog state the same rule.
- [x] Every exit-code claim executed: a trailing-comma settings.json through the real CLI exits 2
      naming the file; the same file well-formed exits 0 and keeps the sole version.
- [x] Script tests: `tests/test_pluginprune.py` covers each case the paragraph names (malformed,
      wrong shape, not UTF-8, unreadable, malformed project file, malformed `~/.claude.json`,
      missing `--settings` / `--claude-json`, whitespace-only, and the well-formed control).
- [x] Security: the diff adds prose only; the script change it documents makes deletion stop on
      every settings source it cannot use.
