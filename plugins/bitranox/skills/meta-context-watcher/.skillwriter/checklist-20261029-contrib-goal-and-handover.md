# skill-writer checklist - meta-context-watcher (an active /goal at handover time)

- [x] Change: SKILL.md step 8 (the `/clear` nudge) - when a `/goal` is running, its check re-fires after every
      turn and the agent can clear it no more than it can run `/clear`; the nudge line names both commands
      (`/goal clear`, then `/clear`), and a re-fired goal check gets that same line and no work.
- [x] Receipt held: `skill_receipt.py check meta-skill-writer` reported "fresh"; the editing agent loaded
      bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] RED as a text check of the pre-edit file (no subagent arm: the batch brief forbids dispatching
      subagents): `grep -rn -i "goal" SKILL.md references/` printed nothing, so the handover steps were silent
      on a running goal.
- [x] GREEN quote-back, found with grep: "**An active `/goal` must be cleared too.**" and the nudge
      "Type `/goal clear`, then `/clear`, to start the next".
- [x] Mechanism claims checked: `/goal clear` is a real subcommand (the CLI binary carries "run /goal clear"
      and "Goal cleared: "); the `goal_status` attachment with `met: false` while a goal runs is the recorded
      shape in real transcripts; built-in slash commands are not model-invocable (the step's existing text).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, `reformat_tables.py --check --strict` reports Unchanged, release-history finder over the
      added lines printed nothing.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for meta-context-watcher.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
