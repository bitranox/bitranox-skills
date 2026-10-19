# skill-writer checklist - coding-python-layered-config (2026-10-19, lib_layered_config 7.2.0)

Two additions, identical in both copies of the skill, in "Python API beyond read_config":

- the deploy paragraph: `force=True` backs up and overwrites, `batch=True` keeps the file and writes a
  `.ucf`;
- a new paragraph "What a deploy sees, before it runs": `deploy_config_paths` (every file a deploy
  writes, `.d` copies included, host's `hosts/<hostname>.d/`), `read_deploy_config` (the deploy's own
  read with `skip` left out: no `.env`, only `user_*`/`enabled` from a user file, `TypeError` for one bare
  path), the errors both raise, and reading the modes through
  `deploy_permissions_from_config(..., overrides=...)`, `.enabled` and `.for_layer(...)`.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: one retrieval scenario (before a forced deploy to app and user, list
      every file it writes and print the modes it applies, computed from the configuration the deploy
      itself reads), answered only from the skill text, old text (RED) against new text (GREEN), inert
      text-only probe (`bitranox:baseline-probe`), model pinned to opus. Both arms received the same
      excerpt: the errors list, the deploy paragraph and the `permissions=` row of Common mistakes.
- [x] Inherited context checked with `redcheck --corpus-cascade` over the source repo: 1588 documents,
      verdict "inherited", strong hit on the source repo's CLAUDE.md, which names both functions in its
      File Permissions section. Adjudicated: the RED ran with that line already in reach and still
      answered NONE for both steps, so the RED stands; the GREEN coverage is proven by a text check
      instead (quote-back below, every answer a direct quote of the skill excerpt). The other hits share
      only common words (configuration, force, modes).
- [x] Scope: one sentence and one paragraph; frontmatter untouched, no routing keyword moved.
- [x] Every claim executed against the 7.2.0 code before it was written: the paths for `user` (file plus
      `config.d/` copy) and for `host` (`hosts/<hostname>.toml` plus `hosts/<hostname>.d/`); the
      configuration read through `read_deploy_config(skip=deploy_config_paths(...))`;
      `deploy_permissions_from_config(..., overrides=...)` giving `.enabled` and `.for_layer("app" |
      "host" | "user")` with `.directory`/`.file` printing as `0o700`; `TypeError` for `skip="x"`;
      `FileNotFoundError` for a missing source; `LayerLoadError` for a broken user file not skipped and
      for a broken source. Pinned by `tests/examples/test_deploy_public_read.py`.

## RED (old text)
- [x] Listing the files a deploy writes: NONE - only the `DeployResult` after the deploy.
- [x] The configuration the deploy reads: NONE - the mistakes row says what it excludes, nothing yields it.
- [x] `force=True`: guessed, the excerpt never named it.

## GREEN (new text)
- [x] Both steps written with `deploy_config_paths`, `read_deploy_config(skip=<that set>)`,
      `deploy_permissions_from_config(...)` and `.for_layer(...)`, no private import.
- [x] Gaps reported and decided: `.d` directory of a non-`config` source, `for_layer` values, the type
      of `.directory`/`.file`, `enabled`, `permission_overrides` in a preview, errors of the new
      functions, Windows - CLOSED in the text. `.d` results inside `DeployResult` - DECLINED, the existing
      deploy paragraph's subject, unchanged here. Version older than 7.2.0 - DECLINED, the paragraph
      names its floor.

## REFACTOR
- [x] Quote-back on the closed gaps: all seven questions answered by a direct quote of the new text.
- [x] Leftover gaps from quote-back: a broken source - CLOSED ("the source included", executed).
      Layer roots - DECLINED, the per-OS paths table in the same skill answers it. `enabled` against
      explicit modes - DECLINED, the errors list and the CLI reference own that rule. `str` vs `repr` of
      a mode, and what `for_layer` reports on Windows - DECLINED, the paragraph says modes are never
      applied there, which is what a preview needs.
- [x] RED/GREEN diffed both ways: nothing the RED produced (error handling, `.action.value`) is missing
      from GREEN.

## Deploy
- [x] Source and mirror identical apart from the three by-convention differences (`repo-gate.py --mirrors`:
      in sync).
- [x] No address, host name or private path added; the reference links in "Full detail" are unchanged.
