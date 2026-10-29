# When the context watcher fires on its own

A hook measures context from the transcript's last recorded usage - the real per-request figure,
not an estimate. The context limit is `min(context_handover_pct of the window,
context_handover_cap)`.

In compact mode the limit is the value `CLAUDE_CODE_AUTO_COMPACT_WINDOW` should hold, set in the
`env` block of `~/.claude/settings.json`. The harness compacts about 33k tokens below that value
(measured on Claude Code 2.1.310), and the hook asks for the checkpoint about a tenth (at least
40k) before that point. It asks on `PostToolUse` as well as on `Stop`, because a long autonomous
turn can pass the whole stretch without stopping once. When the variable is unset or larger than
the limit, the request says so: tell the user once and offer to set it through the update-config
skill. After a compaction the reading falls below the save point, and the next crossing asks for a
fresh checkpoint.

In handover mode the hook blocks on `Stop` once context crosses the limit.

The window comes from the model family on the transcript's most recent assistant record, so nothing
needs configuring for a known family. A model id no family table knows - a gateway model such as
glm-5.3 behind `ANTHROPIC_BASE_URL` - takes the window its launcher declared in
`CLAUDE_CODE_MAX_CONTEXT_TOKENS`, the variable Claude Code defines for exactly that case; the hook
reads it from its own environment. A model that is neither known nor declared falls back to a
200k window that errs small on purpose. In one rule: family table first, then the launcher's
declaration, then 200k - a known family always wins, so a globally exported declaration left over
from another model cannot override a measured family window.

Its warning about the overwrite asks git whether `handover.md` is tracked in the repo it fires in
and says which case applies, because some repos commit the file and others ignore it.

In handover mode, declining is not permanent: the next ask waits until context has grown another
tenth of the window, because a decline at 40% is "not yet" while 90% is a different question.

If it ever reports measuring MORE context than the window, the detection failed - set
`context_window` explicitly via `bitranox:meta-memory-settings`. That is reported rather than
ignored because a threshold nothing can reach looks exactly like a watcher that works.
