# Sessions, agents and shells that outlive a clear

Loaded from `meta-context-watcher` SKILL.md when a backlog line or handover names another
session, or after a `/clear`. A handover-named background agent is covered in SKILL.md itself.

**A peer session a backlog line names may be gone.** Before you ask the user when to hand an item
to another Claude session ("hand X to the <name> session once it finishes Y"), check that the
session still exists: `ListAgents` lists the other local Claude sessions by name. Outside it,
read the registry entries `~/.claude/sessions/*.json` (under `CLAUDE_CONFIG_DIR` when that is
set) as JSON and take the one whose TOP-LEVEL `name` matches; a grep also hits the old names kept
under `formerNames`. No entry means the session ended, and an entry's `pid` takes a
`kill -0 <pid>` check for a crash (observed on Claude Code 2.1.310):

```bash
python3 -c 'import json,glob,sys; print([json.load(open(f))["pid"] for f in glob.glob(sys.argv[2]) if json.load(open(f)).get("name") == sys.argv[1]])' <name> "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sessions/*.json"
```

Sessions end, are cleared or crash, and the line keeps naming them. A question's options must
rest on the current state, not on a line written earlier: asking to schedule a handover to a
session that is gone costs a round trip and promises coordination that cannot happen. If it is
gone, the question changes from "when to hand over" to "who does this now": present the item as
unowned work, and rewrite its line to say so.

**After a `/clear`, look for survivors yourself; the handover may not name them.** Two kinds
outlive the clear: background subagents and `run_in_background` shells. `ListAgents` does not
show this session's shells, nor a subagent that has already finished (measured on Claude Code
2.1.309), so a list with nothing of yours does not mean nothing of yours ran or is running.

- **Shells:** every Bash call's shell is a child of this session's `claude` process (measured on
  Claude Code 2.1.309), so `$PPID` names it, and `ps --ppid $PPID -o pid,etime,args` lists this
  session's shells (beside its MCP servers and the `ps` call's own shell). Other sessions' timers
  on the same host run under their own `claude` process: filter by parent, never by command text.
- **Subagents:** each one's transcript is
  `~/.claude/projects/<project key>/<session id>/subagents/agent-<id>.jsonl`, where the project
  key is the project path with every non-alphanumeric character replaced by `-`. List them all,
  newest first (`ls -t ~/.claude/projects/<project key>/*/subagents/*.jsonl`): the ones written
  just before the clear head the list, whatever the session id. Read each one's prompt and last
  messages before saying what it did; one whose file is still growing is still running. Several of
  them: say which one you report on. Check a branch or worktree its prompt names the way SKILL.md
  checks a handover-named background agent (its branch against origin, its report against what
  was expected of it).
- **An obsolete shell** (a deadline timer for a subagent that has reported) does no work, but its
  completion notice lands here, so stop it. Its argv holds the text you wrote for it, which names
  what it guards; when that text matches no subagent you can find, ask the user before killing it.
  Kill the shell and its child (`ps --ppid <shell pid>` names the child), then
  `ps -o pid= -p <shell pid>,<child pid>` must print nothing. If auto mode refuses the `kill`,
  give the user the `! kill <shell pid> <child pid>` line. Either way treat its notice as stale when it arrives.
