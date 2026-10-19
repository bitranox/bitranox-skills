# STALE - read 2026-10-19, work continued

## In flight

- Nothing part-done. No subagents or background jobs are running. The three `fold23-3b`
  worktrees and branches (bitranox-skills, pwshpy, btx_lib_mail) are removed.

## Committed, or not

- Pushed, CI green on each: bitranox-skills 9.3.1 (`8d91f0b0`), pwshpy 1.5.1 (`c14f119`),
  btx_lib_mail 4.5.1 (`5f548ad`). The two tool repos were pushed, NOT released (no tag, no PyPI),
  as with bmk 3.21.3-3.21.5. The user has installed 9.3.1.
- Memory store (`<softdev-root>/.claude-memory`): still uncommitted, now also holding today's three
  archives, one new fact and two re-pointed facts. Backup taken first:
  `.plan/fold-23/backup-pre-archive-3b.tgz`. The next dream commits it, staging deliberately.
- `EXECUTION-USER-REVIEW.md` (gitignored) holds today's two user decisions verbatim.
- This handover and `OPEN-WORK.md` are committed together.

## Decided, and why - do not reopen

- 3b went ahead on the user's explicit approval this session (verbatim label "Do 3b now
  (Recommended)"); an earlier session's go did not cover these public pushes.
- The btx_lib_mail fact was replaced, not archived whole (user: "New fact for that lesson
  (Recommended)"): its transport part is in coding-python-send-mail; its unrelated merge-file
  lesson is now `reference-port-a-template-fix-to-unrelated-repos-with-git-merge-file-not-git-apply-3way`.
- The pwshpy traps table names the shell per row because measurement on Windows PowerShell
  5.1.26100 and pwsh 7.6.6 showed three of the six are shell-specific; the fact had stated them
  unqualified. Evidence: `plugins/bitranox/skills/coding-python-pwshpy/.skillwriter/checklist-20261018-ps1-traps.md`.
- Declined in both review artifacts, with reasons: a `$args`-forwarding code example (native
  argument passing differs between 5.1 and 7, not measured), and claiming a patched test actually
  DELIVERS mail (measured only up to the SMTP session).

## Still open, untouched

- [23] 3c (provmm-benchmark, private Gitea), [23] Phase 3, [26], [28], [96] and the FOUND items:
  `OPEN-WORK.md`. [590] part (1) looks resolved (`--check-tree` TOTAL 0); confirm and close it.

## Lessons for the next nap

- When folding a memory fact that names a library's internal mechanism into a skill, re-run it
  against the current release first: the btx_lib_mail fact's MagicMock/has_extn story was stale on
  4.5.0, where `patch("smtplib.SMTP")` is never called and the test opens a real socket.
- When a fact states a PowerShell behaviour, measure it under BOTH Windows PowerShell 5.1 and pwsh 7
  before writing it down: the curl alias and native-stderr-under-Stop are 5.1 only, the `-File`
  colon split is pwsh 7 only.
- When a merge across repos with no shared history is checked by exit code, do not trust
  `git apply --3way`: it prints "repository lacks the necessary blob", falls back to a plain apply
  and can exit 0.
- tooling: repo-gate's PUSH gate reads each mirrored twin from its MAIN checkout's `master`; with
  all three repos edited in worktrees, fast-forward each main checkout's local `master` to the
  worktree branch before pushing (the stored stage-and-restore order covers only the commit).
- tooling: `repo-gate.py --mirrors` exits 1 when a tool repo has a linked worktree (listed as
  UNLISTED) even with every pair in sync; read the "N of 12 mirrored pairs have drifted" line.
- tooling: the session's `tail` rejects `tail -3` ("unexpected argument '-3'"); use `tail -n 3`.
- Carried over, not napped yet: the lessons in `git show 90742dd9:handover.md` and those it
  carries over.

## The exact next action

[23] is the top-ranked open item; its next step is 3c. Read the [23] line in `OPEN-WORK.md`, then
check the target is reachable before any edit:
`git -C <softdev-root>/bitranox-systems/provmm-umbrella fetch && git -C <softdev-root>/bitranox-systems/provmm-umbrella status -sb`
(its remote is the private Gitea, so pushes need no confirmation).
Then fold `feedback-benchmark-fair-settings` into
`bitranox-systems/provmm-umbrella/.claude/skills/provmm-benchmark/SKILL.md` through
bitranox:meta-skill-writer, quote-check, and archive the fact.

## Files that matter

- `OPEN-WORK.md` ([23] carries the step state)
- `plugins/bitranox/skills/coding-python-pwshpy/SKILL.md`, `plugins/bitranox/skills/coding-python-send-mail/SKILL.md`
  and their `.skillwriter/checklist-20261018-*.md`
- `.plan/fold-23/` (rows, backups, including `backup-pre-archive-3b.tgz`)

## How to verify

- CI: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`) here, in
  `projects/public/apps/utils/pwshpy` and in `projects/public/libs/btx_lib_mail`.
- Twins: `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` reports 0 of 12 drifted.
- Memory tree: `reconcile_memory_index.py --check-tree <softdev-root>` (home
  `skills/meta-self-improve/`) reports TOTAL 0.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
