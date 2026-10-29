---
name: meta-claude-hooks
description: Use when writing, editing, debugging or reviewing a Claude Code hook - picking a hook event, writing a matcher, choosing a command/http/mcp_tool/prompt/agent handler, working out what arrives on stdin and what to print to allow, deny or inject context, why exit code 2 blocks one event and is ignored on another, why a hook silently never fires, or how to test one without a live session.
---

# Claude Code hooks

Reference baseline: hooks.md, fetched 2026-10-05, 33 events, content db1a798c65b7

Hooks are the deterministic layer around the agent: Claude Code runs your handler at a fixed point in its
lifecycle, so a rule holds whether or not the model decides to honour it.

There are **33 hook events** and **five handler types**. Most people know nine events and one type, which is why
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

| Topic                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Read                          |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| **All 33 events** - SessionStart, Setup, InstructionsLoaded, UserPromptSubmit, UserPromptExpansion, MessageDisplay, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, PostToolBatch, PermissionDenied, Notification, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, SessionEnd, Elicitation, ElicitationResult | `references/events.md`        |
| **Configuration** - hook locations and precedence, matcher patterns and the exact-match vs regex rule, MCP tool matchers, the five handler types, common fields, `if` and Bash pattern matching, exec form vs shell form, HTTP and MCP tool and prompt fields, path placeholders, hooks in skill and subagent frontmatter, `/hooks`, `disableAllHooks`                                                                                                                                                                   | `references/configuration.md` |
| **I/O contract** - common input fields, exit codes 0/2/other, timeouts, exit-code-2-per-event table, HTTP response handling, JSON output, `continue`, `stopReason`, `systemMessage`, `terminalSequence`, `additionalContext`, decision control per event, `updatedInput` and `updatedToolOutput`, reading typed prompts and skill bodies out of the transcript, subagent transcripts, same-message sibling calls                                                                                                         | `references/io-contract.md`   |
| **Authoring** - which handler types each event supports, prompt and agent response schema and `continueOnBlock`, async and `asyncRewake`, testing a hook from stdin, `claude --debug`, traps, no dependency provisioning and the lazy-import degrade, security and workspace trust, Windows PowerShell, environment variables, probing `AskUserQuestion` interactively, write guards and the shell, launchers, value vs structure, prose intent matchers                                                                 | `references/authoring.md`     |

Upstream, for detail beyond these files: <https://code.claude.com/docs/en/hooks.md> (reference) and
<https://code.claude.com/docs/en/hooks-guide.md> (guide). Both serve raw markdown.

## Before you write a hook, answer these

1. **Which event?** Read the index at the top of `references/events.md` rather than reaching for the familiar
   one. If you are about to poll for something, check whether an event already reports it.
2. **Can that event block at all?** Roughly half cannot. Check the exit-code-2 table in `references/io-contract.md`.
3. **Does it take a matcher, and will yours be read as an exact string or as a regex?** Any character outside
   letters, digits, `_`, `-`, space, `,` and `|` makes it an **unanchored** regex, so `Edit.*` also matches
   `NotebookEdit`.
4. **Which handler type, and does that event support it?** `prompt` works on 13 events and `agent` on 12 only;
   `SessionStart` and `Setup` take just `command` and `mcp_tool`, and `Setup` always skips its `mcp_tool` hooks.
5. **How does it answer?** `exit 2`, or exit 0 with JSON. Not both by accident.
6. **What happens when it breaks?** Decide deliberately, because a hook's failure mode is its real behaviour.

## The five that bite hardest

- **`exit 1` does not block.** It is a non-blocking error and the action proceeds. Policy hooks use `exit 2`,
  which blocks on the events in the exit-code-2 table. The worktree events are the exception in the other
  direction: *any* non-zero exit aborts `WorktreeCreate`, and fails `WorktreeRemove` if the directory remains.
- **Exit-0 stderr never reaches Claude.** It goes to the debug log. Use `hookSpecificOutput.additionalContext`.
- **Silence is not approval.** A `PreToolUse` hook that exits 0 with no output has expressed no opinion; the call
  continues through the normal permission flow.
- **A hook that never fires looks exactly like one that fires and finds nothing - and like one that crashed.**
  All three are silent, and fail-open turns a guard's bug into an approval. On the first run of a policy hook,
  look for `Failed with non-blocking status code: ... No such file or directory`.
- **A guard judges the whole pending command.** A `PreToolUse` Bash hook sees the entire command string and the
  state as it was before any of it ran.

## A PreToolUse hook reads files the call has NOT been approved to read

`PreToolUse` runs BEFORE approval. A guard that RESOLVES a path out of the pending command - a
`git commit -F <file>`, a `--config <file>`, any file argument - and opens it is reading a file the
user never approved, and one the Read tool's own permission rules never saw. The path is only a
string the model named.

That is tolerable for a guard that must inspect the content to decide. What is not tolerable is
ECHOING it back: printing the matching lines on `exit 2` hands the model content it may not be
allowed to read, and it is the model, not the user, that the hook is talking to.

**Report a hit in a resolved file by POSITION and CHARACTER, never by quoting the line:**

```
line 1, col 34: U+2014 EM DASH          <- safe: says where and what
line 1: The report - written last week  <- leaks the content of an unapproved read
```

Cap the read as well (a size limit and a line limit), since the path may name something enormous.
Quoting back is safe only for text the CALLER typed inline in the command itself, which the user
approved by typing it.

## Before you escalate a nudge to a block, price it

The replay below is not only for escalations: it also gates a new nudge and any rule change in an
always-running hook (both covered after the five checks below).

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

Five things make the number trustworthy:

- **Run a control arm first.** Replay the guard UNCHANGED and require it to reproduce whatever
  figures are already recorded for it. If it does not, the harness is wired wrong and no number
  from any variant means anything.
- **Price the variant you are actually proposing, not the whole hook.** A narrowing that sounds
  obviously safer can score WORSE than the thing it narrows, and the arm you meant to downgrade can
  turn out to have the HIGHER precision - which inverts the proposal rather than trimming it.
- **Diff firing SETS, not counts, when you narrow a matcher.** A narrowing is quieter whether it
  dropped noise or real work, so a falling count cannot tell the two apart, and the unit tests were
  written from the same imagination as the narrowing. Replay the old and the new predicate over the
  same corpus (`guard_replay.py --firings OUT.jsonl` once per predicate, then diff the two files by
  `id`; or `diffbehave` from the same skill), list what the old set fired on and the new one does
  not, and read every row: each is either data you meant to drop or a real command you went blind
  to, typically one behind a launcher or after a shell keyword (see `references/authoring.md`).
- **Split the firings by trigger arm.** One fire rate hides which arm makes the noise, and an arm
  that sounds as justified as the others can carry nearly all of it. Write the fired commands out
  (`guard_replay.py --firings OUT.jsonl`), re-run the predicate over them with each arm disabled in
  turn (patch the trigger set on the loaded module), count each arm's share, then read a random
  sample of what survives. Called by hand, the predicate needs the same second argument (`cwd` or
  `tool_name`) the replay passes, or path handling differs and some rows land in no arm. Record
  the per-arm figures in the hook's docstring and its CHANGELOG entry. Measured once: one
  launcher arm carried nearly all of a first draft's firings, routine test gates, and dropping
  it cut the rate more than tenfold.
- **Say what your rule cannot classify, before quoting a number.** A predicate declared
  `(command, cwd)` receives the recorded cwd, so a rule about paths can be measured rather than
  guessed; but any shape it cannot decide (an interpreter write exposes no filename) is silently
  outside whatever you measured.

Unit tests prove a guard fires on the shapes you listed. Only a replay tells you whether it is
QUIET on everything else - and a block that is not quiet gets routed around, which leaves you worse
off than the nudge you started with. Record the measurement next to the guard so the next author
inherits the answer instead of re-running the argument. Quote two rates, firings over all calls
and firings over the calls carrying the trigger's precondition, and re-run both after any widening.

Replay real history before a NEW warn-only nudge ships too, not only before an escalation, and
set its budget before you look. A nudge firing on much more than about 1% of commands needs a
stated justification; at several percent it is a dead nudge and drags its working trigger down
with it, because a channel that speaks on ordinary work teaches the reader to skip it. The failure
is invisible from inside the design: every firing matches the pattern you wrote, so each one looks
correct on its own and only the rate shows it.

The same kind of replay gates ANY rule change in a hook that runs every session, escalation or not:
a guard predicate, a signal pattern a hook helper scans for, an exclusion or discount clause. Replay
it over the corpus that rule reads: Bash calls through `guard_replay`, typed prompts through
`corpus_prompts`, transcript text through `jsonl_grep`. The unit tests cover the cases you thought
of; the hook runs over every session, and a green suite can sit beside a changed rule that reports
many more candidates, most of them noise. Classify every firing the change ADDS or REMOVES (the
firing-set diff above), not a sample, reading each against its source transcript. A widening is not
safe by being a fix: a loosened exclusion over-reaches just as a narrowed matcher goes blind. For
a rule that defines a REGION (a heredoc body, a fence, a quoted span), check what the widened
OPENER swallows, not only what it now matches: the region runs to its delimiter, so an opener that
matches too much silences every later line. Measured: dropping the "opener names a test file"
clause let a bare `<<` match a C++ shift operator, and one `cout << x` in a source listing
suppressed the rest of that file.

A rule keyed on what the person TYPED (a router trigger, a prompt-matching nudge) gets the same
firing-set replay over the prompt corpus with `corpus_prompts.py` (home:
`skills/compuse-toolbox/scripts/`), with no precision figure: a prompt has no gate and no exit code.
By default it dedupes by record `uuid` (a resumed or forked session copies the earlier transcript)
and skips tool results, `isMeta` records and subagent briefs, but returns the prompts RAW: also drop
any prompt repeating verbatim more than a handful of times (a person rarely does, a scheduled job
always does) and apply the person tests in `references/io-contract.md`, or you tune against text the
hook never sees. Pick a rule's distinctive tokens by SHAPE (carries a digit or punctuation), not by
LENGTH: measured, a 9-character floor admitted `description`, `condition` and `interface` as
distinctive, while each of the shape rule's 126 tokens reached fewer than 20 prompts.

**A hook that fires on the incident that motivated it is not evidence a detectable signal exists.**
The incident can sit inside a large benign class with the same structure, its hazard carried by a
label or an intent rather than by anything in the command, and then no structural rule separates it
from thousands of harmless calls. When the replay shows that, say so in the hook's docstring and pin
it with a test, rather than shipping the noisy version.

A project's decision log is the common case. A commit-time guard that matches changed files or
identifiers against the log, to stop agents re-attempting a rejected approach, fires on most
commits however it is tightened, because a decision log and its code share their vocabulary: a
filename near a decision word carries almost no information. Measured over 480 real commits, four
successive tightenings fired on 83%, 62%, 34% and 23% of them, flattening rather than converging,
and the motivating incident fired in every variant, in most of them matching the right entry for
the wrong reason. When the decision has an identifiable site in code, put a comment at that site
saying what is deliberately absent and why: it reaches the one reader who can act on it, at the
moment they would re-make the decision.

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
uv run scripts/hookdoc_stamp.py stamp --write     # re-stamp; refuses (exit 2) while coverage has gaps
uv run scripts/hookdoc_stamp.py baseline --write  # refresh the baseline line above
```

Exit codes: 0 current or cosmetic; 1 structural drift, a coverage gap, a stale baseline line, or an unmet
`check --expect`; 2 the run could not look (BROKEN, whatever `--expect` said) or refused the whole action (`stamp`
with gaps, `baseline --write` with no line to update). `--json` prints its envelope on every exit, `ok` false
only on 2.

After a `STRUCTURAL` verdict: update the reference files **first**, then re-stamp. `stamp` runs `coverage` before
writing and refuses while a newly-appeared event is undocumented, so the stamp cannot quietly move ahead of the
documentation it certifies.

`coverage` has two tiers. **Blocking**: every event needs its own heading here, and every name in the
input/output contract, every environment variable and every handler type must appear. **Advisory**: the
per-tool example keys are reported but do not fail, because gating them would fail forever on detail that
belongs upstream, and a gate that can never go green gets switched off.
