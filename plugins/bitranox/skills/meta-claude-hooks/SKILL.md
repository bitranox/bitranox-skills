---
name: meta-claude-hooks
description: Use when writing, editing, debugging or reviewing a Claude Code hook - picking a hook event, writing a matcher, choosing a command/http/mcp_tool/prompt/agent handler, working out what arrives on stdin and what to print to allow, deny or inject context, why exit code 2 blocks one event and is ignored on another, why a hook silently never fires, or how to test one without a live session.
---

# Claude Code hooks

Reference baseline: hooks.md, fetched 2026-08-23, 31 events, content 70c05a3733e6

Hooks are the deterministic layer around the agent: Claude Code runs your handler at a fixed point in its
lifecycle, so a rule holds whether or not the model decides to honour it.

There are **31 hook events** and **five handler types**. Most people know nine events and one type, which is why
the common failure here is not a bug but an absence: building a polling workaround for something a dedicated
event already does, or declaring a capability missing because it is not in the familiar nine.

## The shape of every hook, in one block

Three levels of nesting, always: the **event**, a **matcher group** that filters it, and the **handlers** that run.
Copy this rather than reconstructing it, because the wrapper is the part people invent.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/check.sh", "args": [] }
        ]
      }
    ]
  }
}
```

The event name is a **key**, its value is a **list of matcher groups**, and each group has its own inner `hooks`
list. An event with no matcher support simply omits `matcher`. Full schema in `references/configuration.md`.

## Step 0: check this reference against upstream, before quoting it

The hooks API moves fast - the upstream page carries version-gated behaviour notes spanning many releases, some
of them reversals. Run this first:

```bash
uv run scripts/hookdoc_stamp.py check --json      # from this skill's directory
```

It is cached for seven days, so it normally costs nothing. **In your reply, paste these values from its output:**

```
data.verdict
data.checked_at
data.cached
data.sources[].content_sha256      (first 12 hex)
data.sources[].structure_sha256    (first 12 hex)
data.cli_ahead_of_docs             (true / false / null)
```

If you cannot paste them, the check did not run: say so. Do **not** write "the skill is current" - that sentence
is cheap to produce without looking.

`cli_ahead_of_docs` is a separate signal from the verdict. The check reads your own
`claude --version` and compares it against the newest release the stamped docs mention. When yours is
newer, these files can be a perfect match for upstream and still predate behaviour that changed in
your version - so the check says so and rechecks daily instead of weekly. `null` means the signal is
unavailable (no CLI on PATH), which is not the same as "not ahead".

| Verdict      | Exit | What you do                                                                                                                                               |
|--------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CURRENT`    | 0    | proceed; these files are authoritative                                                                                                                    |
| `COSMETIC`   | 0    | proceed; upstream prose changed but the API surface did not. Say which sections moved                                                                     |
| `STRUCTURAL` | 1    | **stop treating this skill as exhaustive.** Report the added/removed names, read those upstream sections, update the reference file, then `stamp --write` |
| `BROKEN`     | 2    | say "freshness unverified: <reason>". Do **not** say up to date, and do **not** say stale. Keep using the files, flagged as unverified                    |

`BROKEN` is a real answer, not a failure to answer: "nothing changed" and "I never looked" are the same output,
so they must never share a verdict.

## Reference files

Use the Read tool to load the file identified as relevant for full details.

| Topic                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Read                          |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| **All 31 events** - SessionStart, Setup, InstructionsLoaded, UserPromptSubmit, UserPromptExpansion, MessageDisplay, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, PostToolBatch, PermissionDenied, Notification, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, SessionEnd, Elicitation, ElicitationResult | `references/events.md`        |
| **Configuration** - hook locations and precedence, matcher patterns and the exact-match vs regex rule, MCP tool matchers, the five handler types, common fields, `if` and Bash pattern matching, exec form vs shell form, HTTP and MCP tool and prompt fields, path placeholders, hooks in skill and subagent frontmatter, `/hooks`, `disableAllHooks`                                                                                                                                  | `references/configuration.md` |
| **I/O contract** - common input fields, exit codes 0/2/other, timeouts, exit-code-2-per-event table, HTTP response handling, JSON output, `continue`, `stopReason`, `systemMessage`, `terminalSequence`, `additionalContext`, decision control per event, `updatedInput` and `updatedToolOutput`                                                                                                                                                                                        | `references/io-contract.md`   |
| **Authoring** - which handler types each event supports, prompt and agent response schema and `continueOnBlock`, async and `asyncRewake`, testing a hook from stdin, `claude --debug`, traps, security and workspace trust, Windows PowerShell, environment variables                                                                                                                                                                                                                   | `references/authoring.md`     |

Upstream, for detail beyond these files: <https://code.claude.com/docs/en/hooks.md> (reference) and
<https://code.claude.com/docs/en/hooks-guide.md> (guide). Both serve raw markdown.

## Before you write a hook, answer these

1. **Which event?** Read the index at the top of `references/events.md` rather than reaching for the familiar
   one. If you are about to poll for something, check whether an event already reports it.
2. **Can that event block at all?** Roughly half cannot. Check the exit-code-2 table in `references/io-contract.md`.
3. **Does it take a matcher, and will yours be read as an exact string or as a regex?** Any character outside
   letters, digits, `_`, `-`, space, `,` and `|` makes it an **unanchored** regex, so `Edit.*` also matches
   `NotebookEdit`.
4. **Which handler type, and does that event support it?** `prompt` and `agent` work on 13 events only;
   `SessionStart` and `Setup` take just `command` and `mcp_tool`.
5. **How does it answer?** `exit 2`, or exit 0 with JSON. Not both by accident.
6. **What happens when it breaks?** Decide deliberately, because a hook's failure mode is its real behaviour.

## The five that bite hardest

- **`exit 1` does not block.** It is a non-blocking error and the action proceeds. Policy hooks use `exit 2`.
  `WorktreeCreate` is the only event where any non-zero exit blocks.
- **Exit-0 stderr never reaches Claude.** It goes to the debug log. Use `hookSpecificOutput.additionalContext`.
- **Silence is not approval.** A `PreToolUse` hook that exits 0 with no output has expressed no opinion; the call
  continues through the normal permission flow.
- **A hook that never fires looks exactly like one that fires and finds nothing.** Both are silent. On the first
  run of a policy hook, look for `Failed with non-blocking status code: ... No such file or directory`.
- **A guard judges the whole pending command.** A `PreToolUse` Bash hook sees the entire command string and the
  state as it was before any of it ran.

## Before you escalate a nudge to a block, price it

A guard that only warns is easy to escalate on the argument that it demonstrably does not bind: the
recurrence count sits right there and every new hit reads as more evidence. That count is not the
number that decides it. What decides whether a block is an improvement is its PRECISION - of the
commands it would block, how many were going to be blocked or fail anyway.

Measure it by replaying real history instead of reasoning about it. `guard_replay.py` (home:
`skills/compuse-toolbox/scripts/`) takes your predicate and every recorded Bash call in the
transcript corpus and reports the firing rate AND the precision, joining each firing to whether a
gate actually blocked that command:

```bash
uv run <plugin>/skills/compuse-toolbox/scripts/guard_replay.py \
  --module path/to/your-hook.py --func notice --root ~/.claude/projects
```

Three things make the number trustworthy:

- **Run a control arm first.** Replay the guard UNCHANGED and require it to reproduce whatever
  figures are already recorded for it. If it does not, the harness is wired wrong and no number
  from any variant means anything.
- **Price the variant you are actually proposing, not the whole hook.** A narrowing that sounds
  obviously safer can score WORSE than the thing it narrows, and the arm you meant to downgrade can
  turn out to have the HIGHER precision - which inverts the proposal rather than trimming it.
- **Say what your rule cannot classify, before quoting a number.** A predicate declared
  `(command, cwd)` receives the recorded cwd, so a rule about paths can be measured rather than
  guessed; but any shape it cannot decide (an interpreter write exposes no filename) is silently
  outside whatever you measured.

Unit tests prove a guard fires on the shapes you listed. Only a replay tells you whether it is
QUIET on everything else - and a block that is not quiet gets routed around, which leaves you worse
off than the nudge you started with. Record the measurement next to the guard so the next author
inherits the answer instead of re-running the argument.

**The worked example is this plugin's own `hooks/gated-prep-nudge.py`.** Its docstring carries the
figures for both escalations proposed against it - a blanket deny and a target-aware one - and this
section carries the method. That split is deliberate: no number appears in both places, so they
cannot disagree. It also means the two move TOGETHER. If you revisit that guard, update its
docstring AND this section, and if you retire either, the reciprocal pointer in the other becomes a
lie; `hooks/tests/test_gated_prep_nudge.py` asserts both pointers still resolve, so a rename fails
the suite rather than rotting quietly.

## Related skills

| For                                                                  | Use                                          |
|----------------------------------------------------------------------|----------------------------------------------|
| packaging a shipped hook script cross-platform (LF, UTF-8, exec bit) | `bitranox:meta-skill-writer`                 |
| auditing hooks already installed on a machine                        | `bitranox:meta-audit-local-skills-and-hooks` |
| deciding when prose should become a deterministic guard              | `bitranox:meta-self-improve`                 |
| editing `settings.json` itself                                       | the host `update-config` skill               |
| validating untrusted input inside a hook                             | `bitranox:coding-input-sanitization`         |

## Maintaining this skill

```bash
uv run scripts/hookdoc_stamp.py coverage          # offline: every stamped name is documented here
uv run scripts/hookdoc_stamp.py selftest          # proves the drift detector is not a rubber stamp
uv run scripts/hookdoc_stamp.py stamp --write     # re-stamp; refuses while coverage has gaps
uv run scripts/hookdoc_stamp.py baseline --write  # refresh the baseline line above
```

After a `STRUCTURAL` verdict: update the reference files **first**, then re-stamp. `stamp` runs `coverage` before
writing and refuses while a newly-appeared event is undocumented, so the stamp cannot quietly move ahead of the
documentation it certifies.

`coverage` has two tiers. **Blocking**: every event needs its own heading here, and every name in the
input/output contract, every environment variable and every handler type must appear. **Advisory**: the
per-tool example keys are reported but do not fail, because gating them would fail forever on detail that
belongs upstream, and a gate that can never go green gets switched off.
