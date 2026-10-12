# Handover - 2026-10-12 11:30, [200] two more decisions shipped (8.11.1, 8.13.0)

## In flight

- Nothing part-done. 8.11.1 (d4bb74af, mirror gate: a commit passes on a byte-matching
  uncommitted twin) is on origin with CI green. 8.13.0 (40eeeb05, new hook
  `block-write-after-sibling-cd`) is on origin; its CI was still running when this was written -
  check it first (see "How to verify").

## Committed, or not

- Everything above is pushed. This handover and the OPEN-WORK.md edits ([200] note, [560] size,
  new [570]) ship in this handover's commit from the worktree `200-sibling-cd-guard`.
- The MAIN checkout has an uncommitted `# STALE` first line in `handover.md` (marking the
  previous handover read) and sits behind origin. Because this commit changes `handover.md`, a
  plain fast-forward there will refuse; the user runs, from the main checkout:
  `git checkout -- handover.md && git merge --ff-only origin/master`.
  A worktree-isolated session cannot run that for them (git aimed at another checkout is refused,
  a user-typed `!` command included).
- `EXECUTION-USER-REVIEW.md` (gitignored, main checkout) holds today's user decisions verbatim:
  "Accept matching worktree" and "Sibling-aware block" (plus the superseded "Concurrency-aware
  block" entry, marked as such).

## Decided, and why - do not reopen

- The wrong-repo mechanism is NOT a cwd leak between concurrently running calls. Two probes and
  both incident transcripts showed: read-only calls run side by side and keep their own cwd; a
  WRITING call runs after the previous call of the message finished and starts in its final cwd.
  The guard keys on that, which is why it reads earlier siblings of the same message only.
- The guard's refusals (33 of 131,293 replayed calls) include 25 that inherited the directory
  their author wanted; accepted, because the command text cannot tell them from the 5 that went
  wrong, and the cost is one retry with `git -C`.
- The guard is registered under `Bash|PowerShell`: the repo requires every Bash hook to cover
  PowerShell (test_hooks_json_matchers), and `Set-Location`/`git -C` parse the same.
- The mirror-gate acceptance is taken only by a caller that passes a `notices` list, so it can
  never pass silently; a push still reads the other side at what it committed.

## Decided against, and why

- An in-flight-marker hook pair (the queued provmm design): it guards a mechanism that does not
  exist, and would have missed both incidents.
- "Always require a target" for every repo write: the neighbouring nudge's docstring priced the
  cross-message arm at one command in 22; the same-message arm costs 0.025%.

## Still open, untouched

OPEN-WORK.md is the list. [12] its data window opens about 2026-10-13; [18] user-deferred; [96]
waits on shadow data; [200] 5 decision entries left from the original triage, plus 6 entries
other sessions queued on 2026-10-12 (11 open across 8 queues, untriaged); [560] now 11 leftover worktrees; [570] new
(a memory fact states the refuted mechanism, propose-first).

## Lessons for the next nap

- When a guard design rests on a harness mechanism named in a queue entry or memory fact, probe
  the mechanism AND read the incident transcripts before building: "parallel calls share the cwd"
  was wrong, and the shipped design differs from both queued ones.
- When you are about to EnterWorktree, finish any git you asked the user to run in the main
  checkout first: the isolation refuses even their `!` command (recurrence 2, fact already updated).
- When pushing to bitranox-skills behind its ~5 min pre-push gate, ask the live peer sessions to
  hold first: two pushes raced this session's gate before it asked.
- When a repo test pins every Bash hook to PowerShell, register a new shell hook under
  `Bash|PowerShell` from the start and make it read both tools.
- tooling: none new beyond the queued EnterWorktree note ([200]).
- Not yet napped: the lessons in the two previous handovers (`git show 7b92be34:handover.md`,
  which points further back) and in 02ebf096's handover.

## The exact next action

[12] is top-ranked; on or after 2026-10-13 run `classifier_eval.py report` and check its
eligible-row count. Before that date [12] cannot start and [18] is user-deferred, so take [200]'s
next decision: the question-premises nudge that arrives with the answer (provmm-umbrella queue,
`contrib_queue.py list queue_key:e8eb69253790161d`), one question with upsides, downsides and a
recommendation.

## Files that matter

- `plugins/bitranox/hooks/block-write-after-sibling-cd.py` and
  `plugins/bitranox/hooks/tests/test_block_write_after_sibling_cd.py`
- `plugins/bitranox/hooks/shell_text.py` (`statement_program`, `git_segment_dir`)
- `plugins/bitranox/hooks/repo-gate.py` (`mirror_failures`, `notices`, `_say_context`)
- `plugins/bitranox/skills/compuse-git/SKILL.md` (row "A bare `git` after an earlier `cd`")
- `OPEN-WORK.md` ([200], [560], [570])

## How to verify

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha 40eeeb0561c0fe90c3257ee6e241d909550b06cf`
  exits 0 (8.13.0's CI).
- `python3 <plugin>/skills/meta-self-improve/contrib_queue.py queues` lists 11 open entries in 8
  queues as of this writing: the 5 decision entries named in [200] (lsdsk x2, soundtouch-zonemaster,
  provmm-umbrella, bitranox-skills) and 6 new ones from other sessions (projects, bmk fix-60,
  soundtouch-watchdog, lib_layered_config x3).
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML python -m pytest
  plugins/bitranox/hooks/tests/test_block_write_after_sibling_cd.py -q` passes.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
