# Handover - 2026-10-09 13:50, [178] [181] closed; [200] mostly done in 8.10.0

## In flight

- Nothing part-done. Everything this session made is on origin/master with CI green:
  8.9.1 (b556feda: [178] and [181] closed, markitdown non-UTF-8 names, docs skill-count test) and
  8.10.0 (3a1871f5: 20 contribution-queue entries fixed, see CHANGELOG 8.10.0). Release v8.10.0 is
  published.
- [200] (the contribution queue) is the only item worked and not closed: 8 entries remain, all needing
  design or a user decision. They are listed in [200]'s 2026-10-09 note in OPEN-WORK.md and in
  `contrib_queue.py queues` (5 queues).

## Committed, or not

- This handover plus OPEN-WORK.md's "20 fixed" correction (the 8.10.0 commit message and the [200]
  note first said 21; the real count is 20) ship in this handover's commit.
- Uncommitted, outside this repo (both are local backlogs, untracked or excluded by their repos):
  `apps/utils/bmk/OPEN-WORK.md` gained [30] (pip-audit looks up the project itself on PyPI) and [40]
  (devops-bmk twins: empty integration lane, with measured text ready);
  `apps/utils/soundtouch-decloud/OPEN-WORK.md` gained [80] (find's needs-account on the 20.0.6
  adapter) and [90] (document GET /api/setup/devices).
- `~/.claude/commands/tfbpr.md` (user-level, in no repo) now keys the empty integration lane on its
  "no tests collected" output: `make testintegration` exits 2 there, not 5.
- `handover.prev.md` (the outgoing handover) is excluded via .git/info/exclude.

## Decided, and why - do not reopen

- Ten agent worktrees and the integration worktree were removed only after every one of their 41
  changed files was byte-compared equal to 3a1871f5.
- The 40 unused `noqa: E402` directives stay: ruff exempts sys.path.insert, but pycodestyle and flake8
  still flag those imports ([181] closing line).
- infra-modulejail step 5 now RUNS update-initramfs (the blacklist is copied into every initrd anyway,
  so the reboot gate must test that boot) - measured on proxmox01, kernel 7.0.14-5-pve.
- retry-with-a-flag-nudge records only single-statement failures (replay: 30 firings to 5; none of the
  25 removed was a clear true positive).

## Decided against, and why

- devops-bmk and coding-python-new-public-library edits were NOT made here: both skills have twins in
  other public repos (bmk, bitranox_template_py_lib) and need a coordinated two-repo change; filed as
  bmk [40] and bitranox-skills [300].

## Still open, untouched

OPEN-WORK.md is the list. [12] cannot start before 2026-10-13; [18] user-deferred; [96] waits on
shadow data; [200] has 8 entries needing decisions; [530] and [540] were filed today from the 8.10.0
fixes.

## Lessons for the next nap

- When a background task's cwd is a worktree, do not remove that worktree until the task has ended:
  the wrapper's final `pwd` fails with getcwd, and the task reports exit 1 after printing a green
  verdict.
- When several subagents must commit to bitranox-skills in parallel, tell them up front to leave
  their work uncommitted: the repo-gate refuses any plugins/ commit without a version bump, and the
  coordinator bumps once; collect with `git diff --cached --binary <base>` per worktree.
- When collecting subagent output, never trust a file they wrote to the shared session scratchpad:
  two of nine commit-message files there were overwritten by sibling agents; take the text from the
  report itself.
- When the ExitWorktree tool says a worktree holds N commits "not on the original branch", it compares
  against the main checkout's LOCAL master, which may be behind origin; check
  `git merge-base --is-ancestor HEAD origin/master` before believing work would be lost.
- When a contribution entry's claim is triaged, run the hook with a CONTROL that must fire first: a
  probe of block-partial-typecheck from a repo with no root tests/ passed both arms and proved nothing.
- tooling: block-masked-gate-exit refuses a background `pytest ...; echo RC=$?`; background the gate
  alone and read its summary line.
- Not yet napped: every bullet under this heading in the previous handover (`handover.prev.md`, or
  `git show ed243976:handover.md`), which itself points further back.

## The exact next action

Take [200]'s remaining 8 entries one decision at a time (ask the user ONE question per turn, with a
recommendation): start with the skill-edit receipt self-arming entry, which is the same item as [310]
- decide whether `skill-edit-guard` should require a Skill tool call for meta-skill-writer in the
transcript before accepting a receipt. [12] (top rank) cannot start before 2026-10-13 and [18] is
user-deferred, so [200] is the top workable item.

## Files that matter

- `OPEN-WORK.md` ([200], [310], [530], [540])
- `CHANGELOG.md` (8.10.0 entry: what shipped and the replay numbers)
- `plugins/bitranox/skills/meta-self-improve/contrib_queue.py` (`queues`, `list queue_key:<k>`)
- `plugins/bitranox/hooks/skill-edit-guard.py`, `plugins/bitranox/hooks/skill_receipt.py`

## How to verify

- `gh run list --commit 3a1871f5097b604644fed854701dec30ca984640` shows ci and both release
  workflows success; `gh release list --limit 1` shows v8.10.0.
- `python3 plugins/bitranox/skills/meta-self-improve/contrib_queue.py queues` lists 8 open entries in
  5 queues.
- `git worktree list` shows the main checkout only (plus any peer session's own worktree).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
