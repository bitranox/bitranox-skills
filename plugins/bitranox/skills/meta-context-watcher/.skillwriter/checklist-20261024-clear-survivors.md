# skill-writer checklist - meta-context-watcher (2026-10-24, survivors of a /clear include shells)

Two changes. The "In flight" bullet of "What belongs in it" names a surviving `run_in_background`
shell beside a surviving subagent. A new paragraph after "A background agent the handover names as
running is LIVE" says how to find survivors when no handover names them: `ListAgents` does not show
this session's shells or finished subagents, shells are listed by parent (`ps --ppid $PPID`),
subagent transcripts newest first, and an obsolete deadline shell is stopped (or the user gets the
`! kill` line when auto mode refuses it). The LIVE paragraph also names `SendMessage`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique/reference; the test is application - what to check, with which
      commands, when a user asks about "the subagent" right after a `/clear` with no handover.
- [x] Inherited coverage: the memory index held a fact naming surviving shells when RED ran; the
      RED arm still answered without them, so it failed on the text, not on missing context. All
      arms are `bitranox:baseline-probe` (no tools) with the excerpt pasted.
- [x] RED (opus, the pre-change sections): checks only a handover-named agent's branch; never
      looks for a surviving shell; names no rule for telling this session's tasks from a peer's
      ("It gives no rule for telling peer sessions' tasks apart from our own").
- [x] Facts behind the new text measured on Claude Code 2.1.309, not assumed: a Bash call's
      `$PPID` is the session's `claude` process and `ps --ppid $PPID` lists its shells beside its
      MCP servers. The `claude` argv names no
      conversation (a bare `claude` launch carries no `--session-id`), so the subagent rule lists
      transcripts by mtime instead. `ps -o pid= -p <a>,<b>` prints the live PIDs and nothing once
      both are gone (plain `ps -p` always prints a header).
- [x] GREEN (opus and haiku, the edited sections): both list shells with `ps --ppid $PPID`, filter
      by parent, read the transcripts, and give the `! kill` line on a refused kill, each by a
      direct quote of the new text.
- [x] Diffed both ways: the RED arm's branch check survives in GREEN (now also for a subagent no
      handover names); no RED answer lost.
- [x] Gaps, each decided:
      - project-key encoding - CLOSED: "the project path with every non-alphanumeric character
        replaced by `-`".
      - which session dir is the previous conversation - CLOSED by not needing it: "List them all,
        newest first ... whatever the session id."
      - how to find the timer's child and confirm the kill - CLOSED: "`ps --ppid <shell pid>` names
        the child", "`ps -o pid= -p <shell pid>,<child pid>` must print nothing."
      - "harmless" beside "stop it" read as a contradiction - CLOSED: "does no work, but its
        completion notice lands here, so stop it."
      - tying a shell to its subagent - CLOSED: "Its argv holds the text you wrote for it ... when
        that text matches no subagent you can find, ask the user before killing it."
      - several subagents for "the subagent" - CLOSED: "say which one you report on."
      - running versus finished - CLOSED: "one whose file is still growing is still running."
      - branch check for a subagent no handover names - CLOSED: "Check a branch or worktree its
        prompt names the way the paragraph above checks a handover-named agent."
      - `ListAgents` both "named in-process agents" and "shows neither" - CLOSED: narrowed to what
        was measured, "does not show this session's shells, nor a subagent that has already
        finished".
      - sampling interval for "still growing" - DECLINED: judgement.
      - the `$PPID` claim holds for one version - DECLINED: the text states the version measured.
      - `<default>` branch name, reading JSONL fields - DECLINED: general knowledge, owned by the
        caller's context.
- [x] Re-probe on the final text (haiku and opus): all five questions answered by direct quotes,
      no contradiction found; remaining gaps are the DECLINED ones plus the two closed in the last
      edit (child-pid check, no-match case).
- [x] Tiers: RED opus; GREEN opus + haiku; re-probe opus + haiku - 5 cells.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
