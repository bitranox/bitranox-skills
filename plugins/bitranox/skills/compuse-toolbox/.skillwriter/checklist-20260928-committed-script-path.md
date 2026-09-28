# Skill-writer checklist: how a committed script locates a jig (2026-09-28)

Scope: the preamble above the Tools table. It said only "Run from the skill directory, or give the
full path", which leaves a script committed to a repository with one visible path - the version
directory a session announces under `<plugins root>/cache/`. Technique edit; no name, description,
trigger or table row changed.

## RED (baseline, pre-change preamble)

- [x] Inherited coverage checked: `redcheck.py --corpus-cascade` over the dispatch directory read
      1263 documents and flagged all three scenarios, but every top hit shared topic words only
      (`compuse-toolbox`, `ci_wait`, `deps`, `exception`). A search of the loaded cascade and the
      memory facts for the lesson's own terms (`plugins/marketplaces`, `version-stamped`,
      `marketplace clone`) found only a description of where marketplace clones live, written for
      a different purpose, and no rule for committed scripts. The behavioural arm was kept.
- [x] Four arms on the inert probe type, given the old preamble and the base-directory line a real
      session announces:
      - S1 release script, sonnet: glob across `cache/.../bitranox/*/...` plus `sort -V`, and the
        path lacks `scripts/`.
      - S1 release script, haiku: `find ~/.claude/plugins/cache -name ci_wait.py ... -print -quit`,
        which takes whichever version `find` meets first.
      - S2 Python helper, sonnet: glob across the cache plus the highest parsed version, path lacks
        `scripts/`.
      - S3 GitHub Actions script, haiku: `curl` of the jig from the `master` branch at run time,
        then `uv run` on the download.
- [x] Every arm reported a `Skill gaps` section. Shared gaps: no version-independent location for a
      non-interactive script, the jigs' `scripts/` directory not stated, a relocated plugins root
      and CI not addressed.

## GREEN (new preamble)

- [x] Same four scenarios, same tiers, new text pasted in place of the old quote. All four located
      the jig in the marketplace clone with the missing-file guard; S2 built it in Python from
      `CLAUDE_CODE_PLUGIN_CACHE_DIR` or `Path.home()`; S3 no longer downloads anything and falls
      back to a copy committed in the repository.
- [x] The snippet was executed as written: with the clone present it resolved and ran the jig
      (exit 0); with `CLAUDE_CODE_PLUGIN_CACHE_DIR` pointing at a missing root it named the path and
      the install command and exited 2.
- [x] Facts in the text checked against the Claude Code plugin loading reference: the plugins root
      defaults to `~/.claude/plugins` and moves with `CLAUDE_CODE_PLUGIN_CACHE_DIR`;
      `marketplaces/<name>/` is the clone of a git or URL marketplace; a local-directory
      marketplace has no clone and records `installLocation` in `known_marketplaces.json`; a
      superseded version directory is removed 14 days after it is orphaned.

## REFACTOR

- [x] GREEN diffed against RED both ways: the RED gaps (location, `scripts/`, relocated root, CI)
      are closed; no baseline result is missing from GREEN.
- [x] CLOSED: S3 tried the clone first and the committed copy second, so a workstation and CI would
      run different versions of one jig. The copy paragraph now says such a script runs the copy
      everywhere. Verified by quote-back on haiku.
- [x] DECLINED: where in a repository the copy lives, and on what trigger it is refreshed. Those
      are project choices; the text requires a header naming source and version and a deliberate
      refresh, which is what a reviewer needs to see.
- [x] DECLINED: each jig's arguments and where a call belongs in a release flow. `--help` and the
      Tools table own the first; the second is outside this skill.

## Security and hygiene

- [x] Diff reviewed: prose and one shell example; no secret, credential, private hostname,
      address or real user path. The example derives every path from `$HOME` or the documented
      variable.
- [x] The rule forbids fetching a jig from a branch at run time, the unpinned download a baseline
      arm produced.
- [x] No session narrative, operator instruction or scratch path in the skill text or this
      artifact.
