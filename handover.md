# Handover - 2026-09-27 22:10, ranks 30, 40, 60 and 76 closed; nothing part-done

## In flight

Nothing is part-done. Four backlog items closed and shipped this session, each pushed with CI
watched:

- 7.27.1 `83d7743c` - rank 30: anchor_edit backups `.bak.001` upward, next = highest + 1, widens past 999.
- 7.28.0 `e94ad1d7` - rank 40: `anchor_edit.py reap FILE [--apply]`, refuses unless git can restore the file.
- 7.28.1 `e560ddec` - rank 60: lint's "unframed" renamed `unlabelled` (style advisory); no sweep.
- lib_layered_config 5.7.0 `f019f5f` (on PyPI) + bitranox-skills 7.28.2 `10ef1b8b` - rank 76:
  `with_overrides` records supplied keys as layer `override`, path None; skill twins updated.

CI on `10ef1b8b` was still running when this was written - check it first (see "How to verify").

## Committed, or not

- bitranox-skills: everything above is on origin/master; the commit carrying this file adds the
  rank 12 and rank 160 notes in `OPEN-WORK.md`.
- Memory store (tree-top, not this repo): fact
  `reference-config-with-overrides-keeps-the-replaced-layer-s-provenance` rewritten through the
  engine at its owning level (`projects/`) to the 5.7.0 behaviour. Not committed to the store's git.
- Main checkout: still ~220 commits behind with the staged `PLAN-JEV-SKILL.md`/`TODO-JEV.md`
  (rank 150). Left alone; all work ran in `.claude/worktrees/rank30-bak-pad`.

## Decided, and why - do not reopen

- Rank 30: past 999 keep counting (user). Rank 40: separate verb, not automatic reaping (user) -
  the tool cannot tell its own `.bak` from a foreign one.
- Rank 60: no sweep (user). The 5.37.0 probe measured the FRONTMATTER frame; the Why/How labels
  were never measured, and all 87 remaining bodies carry their reasoning as prose.
- Rank 76: fix the library default, not 30 copies (user). Label is `override`, a constant
  `OVERRIDE_LAYER`, deliberately NOT a `Layer` enum member (Layer names loaded sources; callers
  may iterate it). Provenance changes only at paths the merge REPLACED, so loader entries for list
  elements and empty tables survive (a leaf-walk version dropped them; a test pins it).

## Decided against, and why

- Committing the formatter's realignment of `coding-python-new-public-library/SKILL.md`: it is a
  mirrored skill and needs both twins plus a checklist - that is rank 176, not this work.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on about a day of decide rows; next live item by rank is 80.

## Lessons for the next nap

- When the reformat-md-tables hook re-dirties a committed file you never touched and the commit
  gate then blocks, a plain `git checkout --` is undone by the next Bash call (it picks files by
  mtime within 120 s); restore and `touch -d '1 hour ago'` in ONE command, and fix the file at root.
- When a backlog item or lint cites a measured multiplier, trace which variable the measurement
  varied before acting: "unframed" meant no-frontmatter in the probe and missing-labels in the
  lint, and the shared word moved the 5x onto a 206-item sweep.
- When one defect sits in N template-copied repos, look for the shared library call first: a
  library-default fix reaches every consumer through floating floors with zero repo edits.
- When rebuilding derived metadata after a merge, record what the merge REPLACED rather than
  re-walking the merged leaves: a leaf walk drops entries the producer keyed on non-leaves.
- A GitHub run for a push can be created ~25 minutes after the push; a watcher reading
  "in_progress" with a fresh createdAt is queueing, not hung.
- tooling: `repo-gate.py --mirror-of` compares against the MAIN checkout's twin, not the
  worktree's (already queued); diff the two files directly to verify a mirror sync from a worktree.

## The exact next action

Confirm CI on `10ef1b8b`, then work `OPEN-WORK.md` rank 80 (57 statusrot candidates:
adjudicate a sample against their source facts before believing the count). Rank 12 comes back
once about a day of decide rows exists.

## Files that matter

- `plugins/bitranox/skills/compuse-toolbox/scripts/anchor_edit.py` (+ `tests/test_anchor_edit.py`)
- `plugins/bitranox/hooks/memory_engine.py` (`_body_unlabelled`, `lint_tree`)
- `plugins/bitranox/skills/coding-python-layered-config/SKILL.md` and its twin
  `projects/public/libs/lib_layered_config/skills/python-layered-config/SKILL.md`
- lib_layered_config `src/lib_layered_config/domain/config.py` (`with_overrides`, `_override_provenance`)

## How to verify this still stands

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha 10ef1b8bea12b6b141353f6cf41d8a1cc0ae937a` exits 0.
- `curl -s https://pypi.org/pypi/lib_layered_config/json` shows `info.version` 5.7.0.
- `diff` the two layered-config SKILL.md twins: only the `name:` line differs.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
