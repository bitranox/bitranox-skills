# skill-writer checklist - process-agents-subagent-driven-development (2026-11-08, shared worktree and gate.py)

Pre-Flight gains a paragraph: before the first dispatch the controller commits its own edits in
the shared worktree (or gives writers another worktree), and for a vendored upstream or a
markdown-forbidding plan turns the `reformat-md-tables` hook off and checks `git status` after the
first dispatch. implementer-prompt.md runs the full suite through compuse-toolbox's gate.py with a
poll rule for a backgrounded call, and gains a "Committing" section (pathspec only; no amend,
rebase, `add -A` or stash; a refusal over an untouched file is a verbatim BLOCKED). The fix
dispatch copies both parts, with the covering tests as its gate suite.

Decisions: d-20261108-c5d0ebde, d-20261108-176325f3

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill.
- [x] RED by text check, pre-edit text (`git show HEAD:`): 0 hits in SKILL.md and the template for
      "rebase", "gate\.py", "reformatMdTables|reformat-md-tables", a controller-commits-first
      rule; "amend" and "background" hit only unrelated lines (plan amendments, a queue note).
- [x] Mechanism claims checked: `gate.py --help` documents `--gate`, the indented
      `[FAIL] <cmd> (rc=N)` lines and the closing `ALL GATES PASSED` / `GATE RED - follow-up NOT
      run`; `hooks/reformat-md-tables.py` reads `bitranox.reformatMdTables` (OPT_OUT_KEY) and
      covers Write, Edit and Bash events.
- [x] GREEN, the three passages pasted, opus and haiku: S1 controller in a vendored checkout with
      an uncommitted record file, S2 implementer with a 6-minute suite beside a fixer (run,
      correct a commit, a refusal over an untouched file), S3 fix dispatch, S4 a 2 s focused test
      (control: must NOT need gate.py). Both tiers answered every scenario with the quote and kept
      S4 outside gate.py. 2 tiers, 2 cells.
- [x] Gaps closed after GREEN: the full-suite paragraph against "a one-line fix does not need the
      whole suite" (both tiers): the fix dispatch now puts the covering tests in the gate.py
      command as its suite; the opt-out when Bash already ran (at once, then check `git status`);
      the pause between reads of a backgrounded gate.
- [x] Re-run on the final text (haiku, the touched passages): quoted the at-once clause, wrote the
      covering-test gate command, and described the paused polling. No new undecided gap.
- [x] Gaps declined: a total ceiling for a writer's wait (the controller's backstop for the
      dispatch owns that); a commit-message-only mistake (leave it, report it: no amend in a
      shared tree); whether a follow-up commit re-runs the suite (the literal rule holds);
      parallel fixers in one worktree (bitranox:process-agents-dispatching-parallel); the
      attribution line and `$CLAUDE_PLUGIN_ROOT` (File Handoffs and the existing mutation_arm
      line already rely on them).
- [x] Width and fence check over the added lines of both files printed nothing. ASCII only.
