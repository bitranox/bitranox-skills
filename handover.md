# Handover - 2026-10-13 13:05, worktree cleanup done ([560] closed); [9] not started

## In flight

- Nothing part-done. This session only cleaned up: all 16 leftover worktrees under
  `.claude/worktrees/` were removed with `wtclean.py`, each after `landed.py` exited 0 on it, and
  their 16 branches were deleted with `git branch -d` (none refused). No build caches existed.
- CI on 2b617bba (8.18.0) and a90d11c6 (previous handover) is green.

## Committed, or not

- `OPEN-WORK.md` ([560] closed) and this handover are committed together in the handover commit.
- Main checkout is on master, `git worktree list` shows only it.

## Decided, and why - do not reopen

- The 7 `agent-*` worktrees were removed WITH `--discard-uncommitted`: `landed.py` (worktree
  mode) reported every dirty file `in_target`, and one was checked by hand (the worktree blob of
  `block-masked-gate-exit.py` equals its copy in 8a8ad98a, 8.10.3). The user approved explicitly.

## Decided against, and why

- Nothing new.

## Still open, untouched

- lsdsk `OPEN-WORK.md` item `[20]` still restates the pre-7.42.0 exit rule in its `size:` field;
  fix it from an lsdsk session (point the field at the skill). Carried from the previous handover.
- Open sessions run old plugin text until `/reload-plugins` (plus one `/plugin marketplace update`
  per machine).
- A memory consolidation is due (`bitranox:meta-dream-tree`); the user has not been asked yet.
- Everything else: `OPEN-WORK.md`, top item [9].

## Lessons for the next nap

- When auto mode refuses `wtclean.py --discard-uncommitted` after a general "yes" to a cleanup
  plan, ask the user for an explicit "do it" naming the discard: it passed only after that.
- When a batch of worktree-dispatched items ships, remove its worktrees with `wtclean.py` in the
  same session: the cleanup line [560] counted 11 while 16 had piled up by the time it was worked.
- Carried from the 2026-10-13 morning handover (not yet napped):
- When a review loop will not end, look for a backlog or handover line that RESTATES the skill's
  exit rule: sessions resuming with "what next" follow the frozen paraphrase, not the skill.
- When a gate says "a realistic caller reaches it", ask whether the finding is wrong BEHAVIOUR:
  test gaps and doc wording are always "reachable", so a reach-only gate never closes.
- When testing a skill text against a model, run `claude -p --tools "" --disable-slash-commands
  --setting-sources project` from a directory whose cascade assembles 0 documents.
- tooling: a worktree-isolated session refuses `$VAR`-built paths and heredoc-fed python; use
  literal paths and a script file in the scratchpad.

## The exact next action

[9], the top item in `OPEN-WORK.md`: close the soundtouch-zonemaster pushcheck queue entry
(`contrib_queue.py queues`, then `ship --match` on it with queue_key, fixed in 8.17.3), then build
(1), the compuse-toolbox `adjudicate` file mode, TDD with mutation arms in a fresh worktree from
origin/master.

## Files that matter

- `OPEN-WORK.md` (item [9], line 35)
- `plugins/bitranox/skills/compuse-toolbox/scripts/adjudicate.py`,
  `plugins/bitranox/skills/compuse-toolbox/tests/test_adjudicate.py`
- `plugins/bitranox/skills/compuse-toolbox/SKILL.md` (the adjudicate row)

## How to verify

- `git worktree list` prints one line (the main checkout).
- `grep -c '^- \[x\] (2026-10-11) \[560\]' OPEN-WORK.md` prints 1.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
