# skill-writer checklist - git-worktrees (20261117, locked agent worktree: locale and owner)

Change: the existing Quick Reference row "A finished isolated agent's worktree refuses
`remove --force`" is reworded, no new row. It now finds the lock with
`git worktree list --porcelain` (the refusal is localised), takes the branch from that entry,
lists the three removal conditions as one list, confirms the lock pid through `$PPID` and
`~/.claude/sessions/<N>.json`, and removes with `git -C <main checkout> worktree remove -f -f
<exact path>` from outside the worktree, replacing the previous unlock-then-`--force` pair.

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing; the five live rules are
      untouched (inspect-worktree-from-outside is now echoed by "never from inside that worktree").
- [x] Premise check: the queue entry's core (a harness lock outlives the agent; leave another live
      session's lock alone) was already in the row. What it added and the row lacked: the
      localised refusal and the sessions-file owner check. Measured in a scratch repo:
      `remove --force` on a locked worktree exits 128 with `cannot remove a locked working tree`
      under `LC_ALL=C` and `Kann kein gesperrtes Arbeitsverzeichnis` under `de_DE.UTF-8`;
      `list --porcelain` prints `locked <reason>`; `git -C <main> worktree remove -f -f <path>`
      exits 0 and removes it. The Bash tool's `$PPID` is the claude pid, and
      `~/.claude/sessions/<that pid>.json` carries this session's `sessionId`.
- [x] RED: text check of the pre-edit file: `list --porcelain` 0, `.claude/sessions/` 0, `-f -f` 0.
      The pre-edit row keys on the English refusal text only.
- [x] GREEN round 1 (opus and haiku, Q5 and Q6): both wrote `list --porcelain`, the sessions-file
      check and `remove -f -f`, and left a foreign pid alone. Gaps raised and closed: branch name
      ambiguous (now read from the `branch` line of the porcelain entry); where to run git (now
      `git -C <main checkout>`, never inside the worktree); run-on precondition sentence (now
      "only when all three hold"); how to tell a pid is gone (now `ps -p <N>`).
- [x] Declined: landed.py's exit codes (covered by the next row, "only exit 0 (landed) makes the
      discard safe"); which channel to ask another session on (harness-specific, not this
      skill's subject).
- [x] GREEN round 2 (haiku, final text): read the branch from the porcelain entry, checked
      `$PPID` and the sessions file, ran `git -C /opt/repo worktree remove -f -f <path>` and
      `branch -D` from the main checkout, quoting each sentence verbatim. Declined its one new gap,
      a detached worktree with no `branch` line: an isolation agent's worktree always has its
      `worktree-agent-<id>` branch.
- [x] Table re-padded by the formatter after the edit; width and fence check over the added lines
      printed nothing.

Decisions: d-20261117-7ea9b615
