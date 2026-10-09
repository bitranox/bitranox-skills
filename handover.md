# Handover - 2026-10-09 09:40, [170], [173], [245], [390], [450] closed; next is a question about [18]

## In flight

- Nothing part-done. Everything this session shipped is on origin/master with CI green on every
  cell: 8.7.2 (bearer prose, 170.6), 8.7.3 (one hooks fence rule, 170.10), 8.7.4 (skill-script fence
  parity test, mdwrap fix, [450]), 8.8.2 (infra-proxmox ch18 TLS line, [173] closed), plus the
  backlog commit closing [245]/[390].

## Committed, or not

- This handover and OPEN-WORK.md's new [520] are committed and pushed together.
- Gitignored, main checkout only: `.plan/jev-recall-2026-10-06/`, `.plan/jev-stop-2026-10-06/`,
  `.plan/openwork-batch-2026-10-04/` (moved out of the removed jev-shadow worktree, [390]) and
  `.plan/worktree-archive-2026-10-08/{jev-shadow,agent-a8b8519433cd6392c}/`.
- Session B (the [17] mod tools) has ended; its worktree `notify-decide-failed` and five branches are
  still on disk, now [520].

## Decided, and why - do not reopen

- Fence rule (170.10, user chose B, merge): `tell_chars.line_kinds` / `code_line_flags` follow
  CommonMark with indentation judged against the enclosing list item (ported from reformat_tables).
  Neither old rule was right: a census of 13,012 Markdown files showed any-depth closes a block early
  on a nested indented example (our own code-reviewer.md) and 0-3 spaces misses list-item fences.
- The four skill scripts with their own scanner stay standalone (no hooks import); the parity test in
  `plugins/bitranox/hooks/tests/test_fence_walker_parity.py` holds them to the hooks rule instead.
- Bearer rule (D8 A): the value after "bearer" needs a digit or 20+ chars; corpus census 78 prose /
  109 token hits, no token lost.
- U+2192 arrows stay: tell_chars allows them on purpose (122 of the 123 [173] flagged).
- adjudicate's `data.summary.ok` is NOT renamed: it is false exactly on exit 2, the envelope rule.

## Decided against, and why

- Fixing 173.1b (D2 A): already implemented; all 25 `--json` jigs give an exit-2 envelope with
  ok:false on a bad option, and a no answer is exit 1 with ok:true.

## Still open, untouched

OPEN-WORK.md is the list. [12] cannot start before 2026-10-13; [18] is USER, deferred by the user
on 2026-09-27; [177] waits on 13 user decisions; [520] is new.

## Lessons for the next nap

- When copies of one parser are merged, census them on the real corpus first and decide the target
  rule from the disagreements: here each old copy was wrong on a different shape.
- When a parity test passes for copies that already agree, break each copy once and require its
  test to fail before believing it guards them.
- When a mutation arm's pytest exits 4, the run was a usage error (wrong cwd), not a survived
  mutation: read rc 1 vs 4 and the passed/failed counts before drawing any conclusion.
- When a backlog line says "decided, implementation pending", run the behaviour before building it:
  D2 A had shipped with 8.0.0's exit-code work and nobody closed the line.
- tooling: auto mode refused `git worktree remove --force --force` on worktrees whose lock holder pid
  was dead; the user ran it with `!`. Prove the pid dead first, then hand the user the command.
- Carried from session B's 2026-10-09 08:10 handover, not yet napped: record each plugin tool call's
  envelope ok, not only is_error; extract a CHANGELOG section with its trailing blank line when a
  rebase resolver inserts it; expect to lose the master race during the 4-minute pre-push gate and
  re-check new backlog ranks after a rebase; ship a git-init probe to the Windows dev VM from a
  worktree-isolated session; tooling: the isolation guard refuses any Bash text containing "git" in a
  python heredoc.
- Also not yet napped: the lessons of the 2026-10-08 17:10 handover (git history of this file).

## The exact next action

Ask the user ONE question: take [18] ("push down") now, or keep it deferred? It is the top workable
item by rank ([12] waits on a date), but the user deferred it themselves, so starting it is their
call; session B's handover recommended it. If yes: read `.plan/new_placement_rules_plan.md` in the
main checkout (gitignored - copy it first), re-check its file:line references, start with its
section 0 invariant tests in its own worktree. If no: present [177]'s next design question with
options and a recommendation.

## Files that matter

- `OPEN-WORK.md` ([18], [177], [520])
- `plugins/bitranox/hooks/tell_chars.py` (`line_kinds`, `code_line_flags`)
- `plugins/bitranox/hooks/tests/test_fence_walker_parity.py`
- `.plan/new_placement_rules_plan.md` (main checkout, gitignored)

## How to verify

- `git log --oneline origin/master -8` shows 8.8.2 (374fb66f) and the 8.7.x commits.
- `gh run list --commit 374fb66ff98554c8acc344d15b417daea10aba01` shows every workflow success.
- `git worktree list` shows the main checkout and `notify-decide-failed` only.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
