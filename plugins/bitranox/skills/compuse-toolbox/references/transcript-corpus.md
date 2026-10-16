# Walking the Claude Code transcript corpus by hand

Prefer `jsonl_grep`, `guard_replay` or `corpus_prompts`, which walk the whole tree and report how
many files they read; `guard_replay` also dedupes calls by `tool_use` id and `corpus_prompts`
prompts by record uuid. When you must hand-roll a walk or a search over `~/.claude/projects`, each
trap below fails as a plausible NEGATIVE or a slightly-off count, never as an error.

- **Walk recursively: `rglob("*.jsonl")`, never `glob("*/*.jsonl")`.** A main session's transcript
  sits at `<project>/<session>.jsonl`, but a SUBAGENT's sits two levels deeper at
  `<project>/<session>/subagents/agent-*.jsonl`. A shallow walk reads well under half the corpus,
  and it is the half where delegated work is narrated, so a search for something a subagent did
  comes back empty. (An `os.walk` that reports unreadable directories is better still: `rglob`
  skips one silently.)
- **Take the project from the first component under the root**:
  `path.relative_to(root).parts[0]`, never `path.parent.name`, which is `subagents` for a nested
  file.
- **Sanity-check the file count** against `find <root> -name '*.jsonl' | wc -l`; a disagreement is
  the only symptom a shallow walk gives.
- **Dedupe tool calls by `tool_use` id before tallying.** Resuming or forking a session writes a new
  file that begins with a copy of the earlier one, so one real call appears in several files and a
  per-file walk counts it once per copy, inflating the denominator. Skip a repeated id, but never
  collapse records whose id is MISSING, and report how many duplicates were dropped.
- **Task notifications are not `type: "user"` records.** A `<task-notification>` (a background
  command, agent, monitor or workflow finishing or failing) is stored as a `queue-operation` record
  with `operation: "enqueue"` (text in `content`) and as an `attachment` record of type
  `queued_command` (text in `attachment.prompt`). A scan of user records finds none and reads as
  "none happened".
- **Tell a notification's kind by the summary's OPENING words**: `Background command "..."`,
  `Agent "..."`, `Monitor ...`, `Dynamic workflow ...`, `MCP task ...` - match with
  `summary.startswith(...)`, never a substring anywhere in it. The envelope has no kind field, and a
  command whose summary merely mentions "agents" is otherwise filed as an agent failure.
