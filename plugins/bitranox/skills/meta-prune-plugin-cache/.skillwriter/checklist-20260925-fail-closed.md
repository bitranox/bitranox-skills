# skill-writer checklist - meta-prune-plugin-cache (2026-09-25, fail-closed behaviour)

Change: the "Use the tool" section is brought in line with what `scripts/pluginprune.py` now does.
`--apply` re-plans rather than replaying an earlier dry run, and reports only what it actually
removed. Pins spelled `~/`, `$HOME/` or `${HOME}/` count. Paths are compared resolved, a `--keep`
may point inside a version, and a `--keep` matching nothing exits 2. A directory reached through a
symlinked marketplace or plugin directory is refused, an unreadable `installed_plugins.json`
refuses every otherwise unkept version, and an `.in_use` directory that cannot be listed keeps
its version. The text report now names the files it read.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. Test approach: a retrieval arm, seven questions whose
      answers the tool change moved, each answered with a direct quote of the governing text or
      NONE (quote-back), run on the least inferential tier (haiku) with the inert
      `bitranox:baseline-probe` agent type.
- [x] Scope: SKILL.md "Use the tool" section only; frontmatter, description and `name:` unchanged.

## RED

- [x] Inherited coverage checked first: `redcheck --corpus-cascade` over the skill dir read 1250
      documents and reported clean (read as "not caught", not as proof of absence).
- [x] RED, pre-change text: Q1 (can `--apply` remove a `temp_*` the dry run kept) answered "No",
      quoting the shrink-only sentence - wrong, it can. Q2 (a `~/` pin) answered "No" - wrong, it
      is kept. Q3 (corrupt install record), Q4 (mistyped `--keep`), Q5 (failed delete listed as
      removed?) and Q7 (`--keep` inside a version) had no governing sentence. Q6 (symlinked
      marketplace) answered "refused" by generalising "It refuses symlinks".
- [x] RED `Skill gaps` recorded: unreadable settings files, unmatched `--keep`, how `--apply`
      reports failures, parent-path `--keep` matching, the removed-vs-kept output.

## GREEN

- [x] Every question answered correctly with a direct quote of the new text (quote-back), Q6 now
      from the explicit through-a-symlink sentence rather than a generalisation.
- [x] GREEN `Skill gaps`: none reported.
- [x] Diffed against RED in both directions: every RED answer that was right (Q6) is still right,
      now with a governing sentence; nothing the baseline answered was lost.
- [x] RED gap "unreadable settings files" DECLINED here: that behaviour did not change in this
      edit (an unreadable settings file is skipped, as before); documenting or changing it is a
      separate decision.

## Quality

- [x] Frontmatter untouched; `name` and `description` byte-identical, so no trigger moved.
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Word count 1156 (971 before); the added sentences each carry a behaviour a reader acts on
      (an exit code, a keep rule, a refusal), and the tool's `--help` epilog states the same rules.
- [x] Script tests: `tests/test_pluginprune.py` covers every behaviour this section documents
      (74 pass, 1 skipped on POSIX for the Windows-only read-only-file case).
- [x] Security: the diff adds prose only; the script change it documents makes deletion refuse
      or keep on every doubt.
