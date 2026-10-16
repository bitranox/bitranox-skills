# STALE - read 2026-10-16, work continued

## In flight

- `ddcad4c3` (9.1.3, the skill-edit-guard fix) is pushed with CI green. `dc1288c8` (9.2.0, the
  fold) and the commit adding this handover are on local `master` and NOT pushed: the user chose
  "commit, no push, then hand over".
- `dc1288c8` holds the phase-2 fold of [23]: 78 rules in 25 skills, every one GREEN by a
  fresh-context quote-back verifier, every `.skillwriter/checklist-20261016-fold23.md` ticked,
  `repo-gate.py --ci` green before the commit (12605 passed). Also `hooks/bmk-gate-nudge.py`.
- No agents are running. The fold-23 worktree and branch are removed (the branch was identical to
  `master`).

## Committed, or not

- Committed, not pushed: `dc1288c8` (code plus the updated `OPEN-WORK.md`: [23] refreshed, new
  [26], [600], [610]).
- This `handover.md` is committed on top of it in its own commit, also not pushed.
- Memory store: still holds the uncommitted archives and re-points from the previous session plus
  peer sessions' changes; the next dream commits them. Nothing was archived this session.

## Decided, and why - do not reopen

- The fold's RED is a text check (the rule absent from the skill before the edit), not a
  behavioural arm: the rules are still in the always-loaded memory index, so a behavioural arm
  answers from that index with or without the skill text.
- One drafted rule was DROPPED, not softened: an unbalanced backtick in a table row does not lose a
  GFM cell (cmarkgfm and markdown-it-py both render `| x | it`s | z |` as three cells). The memory
  fact that claims it is [610].
- `coding-python-clean-architecture` contracts now run highest-first (composition, adapters,
  application, domain): measured with import-linter 2.15, the old domain-first order reported
  correct code as broken.
- Pointers are archived only AFTER 9.2.0 is installed, or a rule is briefly in neither place
  (plan step 6).

## Still open, untouched

- [12] waits for decide rows (earliest ~2026-10-18). [26] (your new request) and the rest:
  `OPEN-WORK.md`.

## Lessons for the next nap

- When an editor subagent calls a tool "machine-local", ls `plugins/bitranox/skills/compuse-toolbox/scripts/` before accepting it: `ci_wait.py` ships, and the editor wrote generic gh commands instead.
- When subagents fold rules into skills, give the verifier MEASURE items (run the tool, render the markdown, import on the oldest Python), not only quote-back: in 20 skills, 5 drafted claims read correctly and were false when executed.
- tooling: a version bump in bitranox-skills must touch `pyproject.toml` as well as `plugin.json`; repo-gate's version-drift check refuses the gate otherwise.
- The previous handover's ten lessons are not napped yet: `git show 6c1370ea:handover.md` (section "Lessons for the next nap").

## The exact next action

[23] is the top live item. Push and watch CI:

    cd /media/srv-main-softdev/projects/public/KI/bitranox-skills && git fetch && git status -sb
    git push origin master          # pre-push gate ~4 min
    ci_wait.py --ref HEAD           # from bitranox:compuse-toolbox (scripts/)

Then ask the user to run `/plugin marketplace update bitranox-skills` and `/reload-plugins`, and
only then do plan step 6 for the 32 FOLD-THEN-REMOVE pointers (`ref_map.py` first, store snapshot
commit, `reconcile_memory_index.py --archive`, `--check-tree` TOTAL 0, manifest diff) and cap the
57 FOLD-KEEP-POINTER hooks to ~250 chars.

## Files that matter

- `.plan/fold-23/rows.json` (all 1623 classified pointers; which are FOLD-THEN-REMOVE /
  FOLD-KEEP-POINTER), `.plan/fold-23/p2b/` (per-skill phase-2 jobs), `.plan/fold-23/edits-verify.json`
- `~/.claude/plans/curried-mapping-dolphin.md` (the [23] plan; step 6 is the archive procedure)
- `OPEN-WORK.md` ([23], [26], [600], [610])

## How to verify

- `git log --oneline origin/master..master` lists the unpushed commits (expect the fold and this
  handover until the push).
- `grep -l '^- \[ \]' plugins/bitranox/skills/*/.skillwriter/checklist-20261016-fold23.md` prints
  nothing.
- `grep -c '](mem:' /media/srv-main-softdev/CLAUDE.local.md` prints 350 unless peer sessions added
  facts since.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
