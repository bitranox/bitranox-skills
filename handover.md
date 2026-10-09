# Handover - 2026-10-09 12:40, [520] [177] [178] [182] [183] [184] closed; [186] mid-procedure

## In flight

- [186], last item 186.3 (coding-python-gitignore `max_token_bytes` paragraph). User chose option C:
  correct the cause sentence in BOTH twins, bump both plugin.json, and file the root fix in
  lib_layered_config. State: cause measured, RED run, NO file edited yet. The skill-writer receipt
  of this session is not reused - the next session must enter bitranox:meta-skill-writer itself.
  - Measured cause: lib_layered_config 7.0.1 `is_sensitive()` matches `_token_`
    (`max_token_bytes` True, `stdin_chunk_bytes` False). Control: setting
    `IGITTIGITT___LIB_LOG_RICH__SCRUB_PATTERNS__TOKEN=` leaves the value masked; `igittigitt config`
    (2.2.4) has no unredact flag. The skill's "the log scrubber masks any key" is wrong.
  - RED: a haiku baseline-probe given the current paragraph named the log scrubber as the masking
    component and advised against weakening it.

## Committed, or not

- Pushed and CI green: cb4eaa8b ([520], [177]) and 9d378943 ([178] D20 replication note, [96] check).
- OPEN-WORK.md closes of [182], [183], [184] and the [186] state note ship in this handover's commit.
- `.plan/worktree-archive-2026-10-09/notify-decide-failed/` (gitignored, main checkout only) holds
  session B's archived files and `deleted-branches.txt` with the five deleted branch shas.

## Decided, and why - do not reopen

- [18] stays deferred: re-confirmed by the user 2026-10-09.
- No PID nudge ([178] c): user's call after two measurements agreed (2026-10-08: 1 of 189 unshown;
  2026-10-09 replay: 0 of 273, none of the 16 failed ones invented).
- [182]-[184] closed only after each remaining decision was checked against CHANGELOG plus code or a
  run (D7 probed: grep data exit 0, real `pkill -f` exit 2; D21 read from hooks.json).
- [186] keeps the PerformanceSettings one-liner as the workaround until lib_layered_config ships an
  app-declared not-sensitive key set; renaming the igittigitt key would break configs.

## Decided against, and why

- Fixing the redaction inside igittigitt or via its scrub patterns: the scrub patterns do not drive
  the masking, and the heuristic lives in lib_layered_config.

## Still open, untouched

OPEN-WORK.md is the list. [12] cannot start before 2026-10-13; [18] user-deferred; [96] blocked on
shadow data (29 paired max); [200] taken by the peer session bitranox-skills-f0 (coordinate pushes
with it via SendMessage); [290] and below unassigned.

## Lessons for the next nap

- When a backlog item says "measure X first", write the measurement's result and artifact path into
  the item's line the moment it exists: D20 was measured on 2026-10-08 into a .plan archive the line
  never cited, and was re-measured from scratch on 2026-10-09.
- When a doc names the CAUSE of a behaviour (which component masks, blocks or rewrites), run a
  control that removes that component before repeating the claim: emptying the scrub pattern left
  the value masked, which exposed a wrong cause that had shipped in a skill.
- When a "shown earlier" detector matches any numeric token, read its first-match context: ps and
  pgrep output dominate, but short PIDs also match code line numbers, so a 0-unshown result needs
  the coincidental matches checked by hand before it counts.
- tooling: block-masked-gate-exit refused `ci_wait ... > log; echo RC=$? >> log` in a background
  task; run `ci_wait` backgrounded alone.
- Not yet napped: every bullet under this heading in the previous handover
  (`git show cb4eaa8b:handover.md`), which itself carries session B's 2026-10-09 08:10 lessons and
  points at the 2026-10-08 17:10 handover's.

## The exact next action

[186] goes first: it is the top workable open item ([12] waits on a date, [18] is user-deferred,
[96] waits on data) and the user chose its option C this session. Start with
`bitranox:meta-skill-writer` (it issues the receipt), work in a worktree, then edit lines ~189-191 of
`plugins/bitranox/skills/coding-python-gitignore/SKILL.md` to name lib_layered_config's
`is_sensitive()` as the cause, state that the log scrub patterns do not affect it and that `config`
has no unredact switch, and keep the one-liner. Mirror into
`libs/igittigitt/skills/python-gitignore/SKILL.md`. Then a GREEN haiku probe with the same question,
a `.skillwriter/checklist-<date>.md`, `repo-gate.py --mirrors`, bump both plugin.json, ship both
repos, and add the root-fix line to `libs/lib_layered_config`'s OPEN-WORK.md.

## Files that matter

- `OPEN-WORK.md` ([186], [96], [200])
- `plugins/bitranox/skills/coding-python-gitignore/SKILL.md`
- `../../libs/igittigitt/skills/python-gitignore/SKILL.md` (twin, from the public/ tree)
- `plugins/bitranox/hooks/repo-gate.py` (`--mirrors`, `--mirror-of`)

## How to verify

- `gh run list --commit 9d3789433350a927ea643b03c63e1587ddd33bf0` shows ci success.
- `uvx --from igittigitt python -c "from lib_layered_config import is_sensitive; print(is_sensitive('max_token_bytes'))"` prints True.
- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` reports the gitignore pair in sync before
  the edit.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
