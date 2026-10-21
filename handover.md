# Handover 2026-10-21: [23] batch 3b folded (9.10.3 + btx-skill-jev-judge 0.3.1), next the post-install hook cut

## In flight

- Nothing part-done. No subagent or workflow is running, no worktree is left
  (`.claude/worktrees/fold-23-batch3b` merged and removed).
- Waiting on the USER: install bitranox-skills 9.10.3 (`/plugin marketplace update bitranox-skills`,
  then `/reload-plugins`). The hook-cut step below must read the INSTALLED text.

## Committed, or not

- bitranox-skills 9.10.3 (`16aaf6e2`) is on origin/master; CI `ci` + `workflow` green on that sha.
- btx-skill-jev-judge 0.3.1 (`2944dbd`): pushed, CI + CodeQL green, `make release` done (tag
  v0.3.1, GitHub release, PyPI). PyPI's simple index serves it and
  `uvx --from 'btx-skill-jev-judge>=0.3.1' jev-judge --version` printed 0.3.1; the JSON API still
  said 0.3.0 at the time (known lag).
- This commit carries `OPEN-WORK.md` ([23] batch-3b result, new USER item [29]) and this file.
- Gitignored, kept: `.plan/fold-23/batch3/rerun/` (REACH-FAILS rerun, `rerun-merged.json`),
  `.plan/fold-23/batch3/fold18/` (g1-g5 inputs, `pre/` snapshots, `fold-result.json`,
  `retest-result.json`, the workflow script, `qcheck.py`, `mkchecklists.py`), and the three user
  decisions of this session in `EXECUTION-USER-REVIEW.md`.

## Decided, and why - do not reopen

- The 5 REACH-FAILS rows naming a better owner were re-run against it: 0 REACH-OK. All 10
  REACH-FAILS fire while writing hook or transcript-scanner code, where no skill is loaded
  (meta-claude-hooks 5 of 66 hook-editing sessions, compuse-toolbox 1 of 66). Re-owning cannot fix
  that; the candidate fix is a nudge toward meta-claude-hooks on a `hooks/*.py` edit (not yet asked).
- The jev-judge floors went to 0.3.1 in both copies and in `jev_shadow.py` `JEV_JUDGE_FLOOR`,
  because the twin's `test_every_skill_floor_names_the_release_version` and the marketplace's
  `test_the_floor_constant_matches_the_jev_judge_skill` pin them together. The user chose to push
  the marketplace before PyPI served 0.3.1 (a short unresolvable-floor window, now closed).
- The twin's certifi CVE (GHSA-6q48-6c7w-9gw2) is fixed by declaring `certifi>=2026.10.19` in its
  dev "Transitive CVE pins"; bmk then writes the cooldown pin itself. A hand-written
  `exclude-newer-package` entry is dropped by bmk's floor-pin reconcile.

## Decided against, and why

- Folding the 19th REACH-PARTIAL row (feedback-survey-existing-skill-catalogs-...): its skeptic said STAY.
- Folding the attribution-audit half into meta-skill-audit in this release: it is out of the rows'
  owner dirs; queued as a contribution against `skill:meta-skill-audit` instead.

## Still open, untouched

- [23]: post-install hook cut for the 18 rows, then the 10 REACH-FAILS (nudge question), 4 SAFE
  ARCHIVE+REACH-PARTIAL, 2 KEEP-SHORTENED, 2+1 STAY; batch-2 (2b)/(2c), batch-1 (c). See `OPEN-WORK.md`.
- [28] (needs 100 answered subagent shadow rows), [29] (new, needs a scoping question), [440]
  (recurrence bump awaits go-ahead). Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When a handover's next action names counts, recount them from the cited data first: the last one
  said 9 better owners and 18 partial rows, `merged.json` held 5 and 19 (queued against meta-context-watcher).
- When a mirrored skill's text carries a package version floor, check every pin of that floor
  first (the twin's metadata test, `jev_shadow.py`): a skill-only change then needs a package
  release, and the marketplace push has to be ordered around PyPI.
- tooling: bmk's floor-pin reconcile drops a hand-written `exclude-newer-package` timestamp for a
  package no declared floor needs; declare the floor (a CVE pin) and let bmk write the pin.
- When a PreToolUse gate refuses a git command, stage or fetch in a separate earlier command: the
  gate judges the index as it was before the command ran (hit twice this session).
- When a mirrored skill changes on both sides, the twin's branch push is refused until the
  marketplace copy is published; only a tag-only push is unchecked.
- Carried, still uncaptured: strip the blank line after frontmatter before `factedit apply
  --body-file`; read `git show --name-status` (R100) for moves, never `--stat`; quote-test a bold
  lead sentence on haiku; recount every number in an AskUserQuestion from the data; save a fold
  workflow's input builder beside its data in `.plan/`; grep design docs before relaying a "never
  named"; read a predicate's return contract before trusting a replay; redcheck can flag inherited
  on generic terms; fetch origin before blaming a red shared-repo CI; tooling: settings.py accepts
  any value for a knob its choices table does not list.

## The exact next action

`[23]` is the top-ranked open item. After the user has installed 9.10.3: for each of the 18 rows in
`.plan/fold-23/batch3/fold18/g*.json`, quote-check its rule against the installed
`~/.claude/plugins/cache/bitranox-skills/bitranox/9.10.3/skills/<skill>/`, then rewrite the fact's
hook trigger-first, <= 250 chars, ending "Detail: bitranox:<skill>." with factedit (no body change),
at the level that owns its pointer. Then put the meta-claude-hooks nudge to the user as one question.

## Files that matter

- `OPEN-WORK.md` (`[23]`, `[28]`, `[29]`, `[440]`)
- `.plan/fold-23/batch3/fold18/` and `.plan/fold-23/batch3/rerun/rerun-merged.json`
- `plugins/bitranox/skills/meta-self-improve/jev_shadow.py` (`JEV_JUDGE_FLOOR`)

## How to verify

- CI on the head commit: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`).
- Installed plugin: the plugin cache's `9.10.3/.claude-plugin/plugin.json` exists and reads 9.10.3.
- Twin release: `uvx --from 'btx-skill-jev-judge>=0.3.1' jev-judge --version` prints 0.3.1.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
