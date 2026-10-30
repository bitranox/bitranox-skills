# Authoring a hook: choosing a type, testing it, and the traps

## Not every handler type works on every event

Choosing `prompt` or `agent` on an event that does not support it is a silent no-op. The full split:

| Support                                                     | Events                                                                                                                                                                                                                                                                                                        |
|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| all five (`command`, `http`, `mcp_tool`, `prompt`, `agent`) | `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `PermissionDenied`, `Stop`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `UserPromptSubmit`, `UserPromptExpansion`                                                                                                     |
| `command`, `http`, `mcp_tool`, `prompt` (no `agent`)        | `PermissionRequest` - an `agent` hook here is skipped and the permission flow proceeds unchanged                                                                                                                                                                                                              |
| `command`, `http`, `mcp_tool` only                          | `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `Elicitation`, `ElicitationResult`, `FileChanged`, `InstructionsLoaded`, `MessageDisplay`, `Notification`, `PostCompact`, `PostModelSwitch`, `PreCompact`, `PreModelSwitch`, `SessionEnd`, `StopFailure`, `SubagentStart`, `WorktreeCreate`, `WorktreeRemove` |
| `command` and `mcp_tool` only                               | `SessionStart`, `Setup` - but their `mcp_tool` hooks are skipped whenever MCP servers are not yet available: always on `Setup`, and at launch on `SessionStart`                                                                                                                                               |

12 + 1 + 18 + 2 = 33.

## Deterministic or judgment?

Use a `command` hook when the rule is mechanical. Reach for `prompt` or `agent` only when the decision genuinely
needs judgment, because both add an LLM call to the critical path.

| Type      | Cost                       | Use when                                                    |
|-----------|----------------------------|-------------------------------------------------------------|
| `command` | a process spawn            | the rule can be decided from the input, deterministically   |
| `prompt`  | one fast LLM call          | the decision needs reading comprehension of the input alone |
| `agent`   | a subagent, up to 50 turns | verification requires inspecting real files or test output  |

### Prompt and agent response schema

```json
{ "ok": true, "reason": "...", "impossible": false }
```

`ok: true` allows. `reason` is required when `ok` is `false`. `impossible` is optional: the model sets it with
`ok: false` when the condition can never be satisfied, and on `Stop`/`SubagentStop` Claude Code then lets the turn
end instead of looping. **Agent hooks and every other event ignore `impossible`.**

What `ok: false` does varies by event, and the default is often "end the turn", which surprises people:

| Event                                                      | Default on `ok: false`                                                                                                       |
|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `Stop`, `SubagentStop`                                     | reason fed back as Claude's next instruction, turn continues (unless `impossible`)                                           |
| `PreToolUse`                                               | call denied, **turn ends**, reason shown as a warning line. `continueOnBlock: true` returns it as a tool error and continues |
| `PostToolUse`                                              | **turn ends** with a warning line; `continueOnBlock: true` continues                                                         |
| `PostToolBatch`, `UserPromptSubmit`, `UserPromptExpansion` | **turn ends**, regardless of `continue`                                                                                      |
| `PostToolUseFailure`, `TaskCreated`                        | returned as a tool error, turn continues, regardless of `continueOnBlock`                                                    |
| `TaskCompleted`                                            | as a tool error mid-turn; when it fires because a teammate stops, behaves like `TeammateIdle`                                |
| `TeammateIdle`                                             | teammate stops; `continueOnBlock: true` keeps it working                                                                     |
| `PermissionRequest`                                        | **no effect.** Use a command hook returning `decision.behavior: "deny"`                                                      |
| `PermissionDenied`                                         | **no effect.** Only `retry` is read, and prompt/agent hooks cannot set it                                                    |

`continueOnBlock` exists on `prompt` hooks only. An `agent` hook always behaves as if it were `true`.

Before v2.1.210 a `PreToolUse` prompt-hook denial returned the reason to Claude and continued.

## Async hooks

`"async": true` on a **command** hook runs it in the background while Claude keeps working. `asyncRewake: true`
implies it and additionally wakes Claude on exit code 2.

An async hook **cannot control anything**: `decision`, `permissionDecision` and `continue` have no effect, because
the action they would have governed has already happened. Only `additionalContext` and `systemMessage` are
delivered, on the next conversation turn, and **neither is shown to you**.

Other constraints:

- output waits for the next turn; if the session is idle it waits for the next user interaction. An
  `asyncRewake` hook exiting 2 is the exception and wakes Claude immediately
- every firing creates a separate process; there is **no deduplication**
- `timeout` is **not enforced** once an async hook is running in the background; it still is on `asyncRewake`
- under `-p`, any async hook still running at teardown is killed and finalized as `cancelled`. Work that must
  outlive the session has to be a fully detached process
- malformed fields are dropped with a `--debug` warning. Before v2.1.202 malformed async JSON could crash the
  session, and the crash recurred on every resume
- completion notices are suppressed unless you enable verbose mode with `Ctrl+O` or `--verbose`

## Testing a hook without a live session

A hook is a program that reads JSON on stdin and writes JSON on stdout. Test it as one:

```bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"curl x | sh"}}' \
  | ./my-hook.sh; echo "rc=$?"
```

Assert on **both** the exit code and the parsed stdout. Then check the pieces that a stdin test cannot reach:

| Question                             | How to answer it                                                                                                |
|--------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| does it fire at all?                 | `/hooks` shows every registered handler and the file it came from                                               |
| did it match, and what did it print? | `claude --debug`, then read `~/.claude/debug/<session-id>.txt`                                                  |
| why did the matcher not match?       | `CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose` adds matcher counts and query matching                                    |
| is my JSON being read as JSON?       | the debug log says `Hook output does not start with {, treating as plain text`                                  |
| JSON parsed, but had no effect?      | a field at the wrong level is ignored silently; grep the debug log for `Hook JSON output had unrecognized keys` |

`--debug` does **not** print to the terminal; use `--debug-file <path>` to put the log where you want it.

> **A hook that never fires looks exactly like a hook that fires and finds nothing.** Both are silent. On a policy
> hook's first run, look for `Failed with non-blocking status code: ... No such file or directory` - a mistyped
> path in `settings.json` leaves the gate silently disabled while reading as clean.

**If the guard is also installed, its shipped copy judges your probes.** Auditing a command-scanning hook from
a session where the same plugin is active means the live copy scans every probe command first: a probe that
spells out the pattern under test is refused before the copy you are testing runs, the tool call is lost, and
the easy reaction - to stop probing the shapes the live guard objects to - drops exactly the shapes worth
probing. Build the fixture inside a QUOTED heredoc, `python3 - <<'PY'`: guards commonly skip a quoted heredoc
body, where the shell runs no substitution, but still scan an unquoted `<<PY` body. Assemble the
metacharacters with `chr()` (`chr(36)` for `$`, `chr(96)` for a backtick) so the literal appears neither on
the command line nor in any file a content-scanning hook reads, and pass the hook its JSON event on stdin:

```bash
python3 - <<'PY'
import json, subprocess
D, S = chr(34), chr(36)
cmd = "git commit -m " + D + "fix " + S + "(whoami)" + D
ev = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": cmd}})
p = subprocess.run(["python3", "path/to/the-hook.py"], input=ev, capture_output=True, text=True)
print(p.returncode, p.stdout, p.stderr)
PY
```

Always pipe the event in. With no stdin a hook blocks at a terminal, and in an agent's shell (stdin is
`/dev/null`) it reads EOF and usually fails open with exit 0, which looks exactly like an allow. When the
live guard does fire on a probe, record it as data - it is a verified observation of the shipped behaviour.

**A test that launches the hook through a bash shim must not name a bare `bash`.** On a Windows runner
(`windows-latest`), `subprocess.run(["bash", shim, script])` resolves to the WSL launcher in `System32`, not Git
Bash: it prints UTF-16 and exits 1, so the test fails there while every Linux and macOS cell stays green. Either
skip that test on Windows (`@pytest.mark.skipif(sys.platform == "win32", reason=...)`, and cover the hook itself
by running its script directly with `sys.executable`), or resolve Git Bash's own `bash.exe` explicitly and pass
that path. Never rely on `PATH` lookup for `bash` in a test that must pass on Windows.

**An interactive-only tool needs an interactive probe.** Headless `claude -p` does not offer `AskUserQuestion`
(observed on CLI 2.1.296; check `ExitPlanMode` the same way), so the model reports no matching tool and the hook
never fires - a non-answer that looks like a hook that found nothing. Probe in a real interactive session under
tmux, with a throwaway settings file in a scratch directory that registers a `PreToolUse` hook (matcher
`AskUserQuestion`) which appends its stdin to a log and denies with a unique marker string:

```bash
tmux new-session -d -s probe -c /path/to/scratch "claude --settings /path/to/scratch/settings.json"
tmux capture-pane -t probe -p          # the folder-trust prompt: answer it with send-keys
tmux send-keys -t probe -l 'ask me which of two options I prefer'
tmux send-keys -t probe Enter
tmux capture-pane -t probe -p          # what the person would see; then read the hook's log
tmux kill-session -t probe
```

Observed that way: a `permissionDecision: "deny"` stops the call BEFORE the dialog opens and the model receives
the `permissionDecisionReason` verbatim, as `PreToolUse:AskUserQuestion hook error: <reason>` (CLI 2.1.296),
while `additionalContext` reaches the model only together with the person's answer (CLI 2.1.289). So of the two,
only a deny can make the model rework a question before the person reads it. Re-probe after a CLI upgrade.

## Traps worth knowing before you write one

**Exit 1 does not block.** It is a non-blocking error and the action proceeds. Policy hooks use `exit 2`, which
blocks on the events listed in the exit-code-2 table in [io-contract.md](io-contract.md). The worktree events are
the exception in the other direction: *any* non-zero exit aborts `WorktreeCreate`, and fails `WorktreeRemove` when
the directory still exists afterwards.

**Exit-0 stderr never reaches Claude.** It goes to the debug log. To get a message to Claude, use
`hookSpecificOutput.additionalContext`, or exit 2 on `PostToolUse`/`PostToolUseFailure`.

**Silence is not approval.** A `PreToolUse` hook that exits 0 with no output has expressed no opinion, and the
call continues through the normal permission flow. Only `deny` denies.

**A timed-out `PreToolUse` hook does not block.** Do not use a hook that might hang as a gate, unless it sets
`"onFailure": "block"` (`io-contract.md`, "Blocking when the hook fails").

**A decision printed by a background process arrives too late.** Claude Code stops reading a hook's output
shortly after the hook's own process exits, so a `deny` a backgrounded child prints afterwards blocks nothing.
Print the decision first, then start the background work with its stdout and stderr redirected; a hook that
prints an allow and leaves a background child holding the output is blocked, with `refusing to honor the
suspect capture` in the error.

**Skill frontmatter hooks have per-source limits.** The skills from one source (the project, the personal
skills folder, each plugin) can register at most 1,024 hooks per session, with matchers totalling at most
16,384 characters; a skill past the limit runs with none of its frontmatter hooks, and the debug log names it
with `registers none of its hooks`. Under the `strictPluginOnlyCustomization` managed setting only plugin,
bundled and managed skills keep theirs. When a skill's hooks do not fire, `/hooks` in that session shows
whether they registered at all.

**A nested quantifier over alternatives backtracks exponentially on input that does NOT match.** A matcher
such as `\bgit(?:\s+-C\s+\S+|\s+--?\S+)*\s+commit\b` is instant on the short strings a test uses and on any
command that matches. When the repeated group can match the same text in more than one way (here `--?\S+`
reads `--opt` as `-` then `-opt`, or as `--` then `opt`) and the required tail is absent, the engine retries
every combination before it gives up. Measured with CPython `re` on `git` plus N options plus `status`:
under 1 ms at 10 options, about 2 to 3 s at 22, roughly doubling per option. Non-matching input is the
common case for a per-call matcher, so in a `PreToolUse` hook, or in a helper module every hook imports, a
long non-matching command stalls the hook (seconds at 22 options, doubling with each one more), and once it
passes the hook's timeout the call proceeds unguarded (the line above). For "is this command X with
options?", split into tokens and walk them: linear, and it handles two-token options such as `-C <path>`. If
a regex is unavoidable, make the repeated group unable to match the same text two ways (`--?[^\s-]\S*` takes
the same 22 options in microseconds), or use an atomic group or possessive quantifier (`re` on Python 3.11+,
or the third-party `regex` module). Time the matcher on long NON-matching input, and suspect this shape when
a suite's runtime jumps for no structural reason.

**Stdout must be only the JSON object.** A shell profile that prints a banner breaks parsing.

**The 10,000 character cap** applies to `additionalContext`, `systemMessage`, `initialUserMessage` and plain
stdout, each string on its own, and cannot be raised. Longer output is written to a file and replaced with a
2,000-character preview plus the path, and Claude is not asked to read the file, so anything appended after a long
block never reaches context.

**Sections sharing one capped injection get the remainder, never a fixed share.** Overrunning the cap hides every
section behind the preview, not just the one that overran, and no section can know its safe share in isolation.
Assemble the other sections first, pass what they left as the budget, fill it item by item, and degrade to a
one-line pointer (a count plus where to read the rest) when there is no room. A fixed share passes a test that
populates two sections and overruns when a third is present, and a guaranteed minimum breaches the very ceiling it
protects; test with every section that shares the cap populated.

**A guard judges the whole command it is handed.** A `PreToolUse` Bash hook sees the entire pending command
string and evaluates state as it was *before* any of it ran. A compound command that prepares state and then acts
is judged on the pre-command state.

**A guard that scans the raw command string blocks its own documentation.** That string also carries data:
heredoc bodies, quoted message arguments such as `git commit -m "..."`, prose being written to a file. So a bare
substring match fires on a doc or commit message that merely MENTIONS the pattern. Strip the data regions first
(heredoc bodies at minimum, ending at the terminator so a real invocation after the heredoc is still seen) and
match the token's structural position: is it the actual subcommand, after skipping `VAR=` assignments and global
options like `-C`? Skip launchers too (`nice`, `ionice`, `timeout`, `sudo`, `env`, `command`, `exec` and the like)
and the shell keywords a statement can open with (`if`, `while`, `until`, `do`, `then`, `else`, `!`), or the walk
goes blind to real commands written behind them, such as `nice -n 19 git commit` or `do git push`. Keep the
launcher list a FIXED allowlist widened on evidence, never "any leading token is a launcher", which turns
`ssh host 'git commit'` back into a local commit. A narrowing like this is quieter whether it dropped noise or
real work, so diff the old and the new predicate's firing SETS over one corpus before shipping (SKILL.md, "Before you
escalate a nudge to a block, price it"). Require a whole token, not a word boundary (`\bpgrep\b` matches
inside a filename such as `block-pgrep.py`; `(?<![\w-])pgrep(?![\w.-])` does not). Strip heredocs exactly ONCE: a
stripper that keeps the opener line and drops the body is not idempotent, so a second pass sees an unterminated
opener and swallows every line after it; when you need positions, blank the data regions in place and slice
values from the raw text at the same offsets. The same split governs quote and substitution masking: mask to read
STRUCTURE (where statements start), but read every VALUE you compare (two `-C` paths, a redirect target) from the
raw text. Equal-length filler makes two different quoted paths compare EQUAL, so `git -C "$PLAN"` beside
`git -C "$PROX"` and `git -C "$PLANNING"` beside `git -C "$PROX"` get opposite verdicts, decided by a variable
name's length. If the masking preserves length, cut the raw string at the masked text's offsets; if not, record
spans. Normalise the extracted value separately, for its own reasons (strip quotes, a trailing slash). Tests with
literal paths cannot see this: add two different quoted values of the same length, and whenever a scanner
compares two extracted tokens, check which string it read them from. Do not mask quoted strings when the guard's
subject is a command inside a quoted argument that something else executes (`ssh host '...'`, `bash -c '...'`).
Test both directions: text mentioning the pattern passes, and a genuine invocation, with quoted operands or after
a heredoc, still blocks.

**Split a shell command by the TOOL that will run it, never by the host OS.** A `Bash|PowerShell` matcher
receives two languages, and they are mirror images. The Bash tool is a POSIX command line even on Windows,
where Claude Code runs it through Git Bash: `\` escapes, a backtick opens a substitution, `<(` is process
substitution, and `shlex.split` reads the line as the tool does. The PowerShell tool is a Windows command
line: `\` is a path separator, a backtick escapes, and `shlex` eats the separators, turning
`git commit -F C:\Users\me\msg.txt` into the path `C:Usersmemsg.txt`. A guard that then opens that path
fails to read it, fails open, and approves the commit it exists to inspect. Key every split, escape and
separator decision on the event's `tool_name`. Do not reuse a splitter keyed on `os.name` or
`sys.platform`: that key is right only for a command line the machine itself will run (a hook registration
read from a settings file), and on a Windows host it hands the Bash tool's POSIX string to the Windows
parser. Pass the event's raw `tool_name` through rather than defaulting a missing one, and for a tool you do
not recognise pick the reading whose mistake is visible: in a separator or escape walk, escape nothing,
because treating `\` as an escape swallows the `;` after a Windows path and hides the command behind it
(`cd C:\; git commit -m x`), while an extra separator only costs a false block. A mangled token matters
only where the guard RESOLVES it (opens, stats or executes it); tokens merely compared or name-matched
survive. Run the scanner's whole test matrix once per shell tool, not only with `tool_name="Bash"`. The
mirror trap sits in the tests: a fixture that interpolates `str(tmp_path)` into a Bash-tool command fails
only on the Windows cell, because the Bash split correctly eats the backslashes and the hook resolves
nothing. Pass `path.as_posix()` (`C:/Users/...`, what a Git Bash user types) and leave the hook alone.

**A guard about FILE WRITES must match the shell too.** `cat > f <<'EOF'`, `tee f`, a `>` redirect, or
`python - <<'EOF'` opening a file all write without touching `Write` or `Edit`, and in one measured transcript
corpus about half of the writes that carried a decision went that way. The tool a write arrives through is the
agent's choice, not a property of the write, so a `Write|Edit` matcher looks complete, stays green, and is
blind. Register on `Bash|PowerShell` as well as the file tools (see [io-contract.md](io-contract.md)) and match the
redirect or heredoc target, and in PowerShell the `-Path` or `-FilePath` of `Set-Content`, `Add-Content` and
`Out-File` as well as a `>` redirect; put a heredoc case and a redirect case in the guard's tests, since a guard exercised
only through `Edit` passes its own tests forever. Where it cannot cover the shell (an interpreter write exposes no
filename), say so in a comment where it is registered, and add a second gate at a choke point that sees the
RESULT, such as a pre-push hook or a CI check on the changed file.

**A matcher that decides on INTENT in prose is defeated by formatting its author never wrote.** A guard reading a
prompt or a dispatch message gets tested in its author's own spelling, so write the case list before the regex:
the bare sentence, the same sentence behind a list bullet (`- `), behind a short label (`IMPORTANT: `), and with
typographic punctuation (U+2019 as the apostrophe of `don't`); then the negatives - a sentence stating the
OPPOSITE in the same words (an exception clause: "do not use any tools other than Read") and prose that merely
discusses the subject. Normalise punctuation before matching rather than enumerating quote characters. Refuse any
length cap or window you cannot justify: it fails by MISSING, the same silent direction as the bug, so where a
bound is unavoidable make it fail loud. Keep the plain case as a permanent test beside the widened ones, and pin
each newly accepted false positive with its own test. This plugin's `hooks/subagent-probe-capability-gate.py` is
a worked example.

**`if` fails open.** When the Bash command cannot be parsed, the handler runs regardless of the pattern. Use the
permission system for a hard allow or deny.

**A watcher hook can retrigger itself.** See the `FileChanged` guard note in [events.md](events.md#filechanged).

**Hooks cannot set the session model, and see it only at three points.** `SessionStart` may carry a `model`
field, not reliably. From CLI v2.1.251, `PreModelSwitch` receives `from_model`/`to_model` for a switch you or a
client requested and can **block** it (exit 2, or `deny`), but it cannot choose a different target; and
`PostModelSwitch` sees every change, including automatic fallbacks, after the fact. No hook can make a switch
happen. See `bitranox:process-agents-subagent-driven-development`.

**A retrospective hook cannot prevent anything.** If the point is to stop an action, hook the pending action
(`PreToolUse`), not the aftermath. Running the retrospective one more often, or widening the stretch it inspects,
does not fix this: the gap is between the action and the next tick, so periodicity is the defect and window size
is not a dial on it. There is no "every N turns" event either: a periodic supervisor is a `Stop` or `PostToolUse`
hook reading back over the transcript, so it reaches its verdict after the destructive call has already run,
while a `PreToolUse` arm judging the same command reaches it before.

**A hook that crashed looks exactly like a hook that allowed.** Fail-open is the right default, because a hook
must never wedge a turn, but it means an internal error (a bad path, a missing library, a payload shape you did
not model) exits 0 and the action proceeds, and exit-0 stderr reaches only the debug log. So a bug in a guard
presents as approval rather than as a failure, and the guard reads as working right up until you check. Test the
error paths as deliberately as the matching ones: feed it malformed JSON, empty stdin, and an input shape it does
not model, and assert the verdict you intend rather than merely that nothing raised.

## Your handler runs with no dependency provisioning

Claude Code spawns the handler as a plain subprocess. Nothing creates or activates a virtualenv for it, and
inline script metadata (PEP 723) is honoured only by a runner such as `uv run`, never by a bare
`python3 my_hook.py`. The interpreter that runs your hook therefore has whatever its own site-packages happen to
hold on that machine, which on a user's machine is usually nothing you installed. Combined with fail-open, a
missing library does not announce itself: the import raises, the hook exits 0, and the gate is off.

Two ways out, in order of preference:

1. **Write the hook against the standard library.** Reading JSON, matching text and deciding is stdlib work.
   Reach for a library only when the format genuinely needs a parser.
2. **Import it lazily, guarded, and degrade to SKIPPED - never to a pass.**

```python
def validate_xml(text: str):
    try:
        from lxml import etree                                  # preferred parser
    except ImportError:
        try:
            from defusedxml.ElementTree import fromstring       # hardened stdlib fallback
        except ImportError:
            return None                                         # SKIPPED, not "valid"
        return _check(fromstring, text)
    return _check(etree.fromstring, text)
```

The `None` carries more weight than the import does. A hook that reads "the library is missing" as "the input is
fine" becomes a silent no-op on exactly the machines that lack it, and its tests stay green everywhere because
the author's machine has the library. Assert the skip path explicitly, in an environment that really lacks the
dependency.

A third option exists and is usually the wrong trade: make the command `uv run --script my_hook.py` and let PEP
723 metadata resolve the dependencies. That makes `uv` a hard prerequisite for your hook to run at all, and pays
a resolve step per invocation - cached, but not free, and on `PreToolUse` it is every tool call.

## Security

> Command hooks execute with your full user permissions. They can modify, delete or read anything your account
> can. Review and test before adding them.

**Workspace trust differs by session type**, and this is the sharp edge:

- **interactive**: hooks from every settings file, including your own `~/.claude/settings.json`, are held back
  until you accept the workspace trust dialog for the folder or a parent
- **`-p` or SDK**: the dialog never appears and the folder is treated as trusted, so hooks committed in a
  repository's `.claude/settings.json` **run in a folder you have never trusted**

Before scripting `claude -p` over a repository you did not write: review its `.claude/` settings, start with
`--bare`, or disable hooks for that run with `--settings '{"disableAllHooks": true}'`.

Practices:

- validate and sanitize input; never trust it blindly
- always quote shell variables: `"$VAR"`, not `$VAR`
- block path traversal; check for `..`
- use absolute paths. In exec form use `${CLAUDE_PROJECT_DIR}` with no quoting needed; in shell form wrap it in
  double quotes
- skip sensitive files: `.env`, `.git/`, keys

For input validation at a boundary, see `bitranox:coding-input-sanitization`.

## Windows

Set `"shell": "powershell"` on a command hook. Claude Code auto-detects `pwsh.exe` and falls back to
`powershell.exe` (5.1).

Placeholder handling in PowerShell shell form is version-dependent and easy to get wrong:

- write `${CLAUDE_PROJECT_DIR}` or `$env:CLAUDE_PROJECT_DIR`. As of v2.1.198 Claude Code rewrites the
  `${...}` placeholders to PowerShell's `${env:NAME}` form wherever the hook is defined. Before that, the rewrite
  applied to plugin hooks only
- because it resolves after parsing, the placeholder works inside **double**-quoted strings but never inside
  single-quoted ones
- **never write the bare `$CLAUDE_PROJECT_DIR`**: PowerShell parses it as an undefined local variable and
  resolves it to `$null`, silently stripping the project-root prefix from your script path. Claude Code does not
  rewrite that form; it logs a warning in the debug log

The `$env:` form works on every version:

```json
{ "type": "command", "shell": "powershell",
  "command": "& \"$env:CLAUDE_PROJECT_DIR\\.claude\\hooks\\check.ps1\"" }
```

To run a `.ps1`, `.cmd` or `.bat` file, or an `.exe` whose path holds a variable, set `"shell": "powershell"` and
put `&` before the quoted path, as the `check.ps1` example above does.

**Without Git Bash** a shell-form hook with no `shell` set runs in PowerShell, where a hook written for Bash can
fail, and a failing `PreToolUse` or `PermissionRequest` hook then blocks the call (`io-contract.md`, "Blocking when
the hook fails"). Install Git for Windows, or set `CLAUDE_CODE_GIT_BASH_PATH` to the `bash.exe` Claude Code did
not find, then start a new session. A PowerShell guard hook that must block on failure needs both
`"onFailure": "block"` (so it still blocks once Git Bash is found) and `"shell": "powershell"` (so it keeps running
in PowerShell).

For cross-platform packaging of a shipped hook script - LF endings, UTF-8, the interpreter probe, the exec bit,
fail-open discipline - see `bitranox:meta-skill-writer`, section "Bundled scripts and hooks". For auditing hooks
already installed on a machine, see `bitranox:meta-audit-local-skills-and-hooks`. To edit `settings.json`, use the
host `update-config` skill rather than hand-editing.

## Environment variables a hook can read

| Variable                        | Set to                                                                                                                                                                                      |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CLAUDE_PROJECT_DIR`            | project root                                                                                                                                                                                |
| `CLAUDE_PLUGIN_ROOT`            | plugin install dir; changes on every plugin update                                                                                                                                          |
| `CLAUDE_PLUGIN_DATA`            | plugin data dir; survives updates                                                                                                                                                           |
| `CLAUDE_ENV_FILE`               | on `SessionStart`, `Setup`, `CwdChanged` and `FileChanged`: a file whose `export` lines persist into later Bash commands (from `CwdChanged`/`FileChanged` only until the next `CwdChanged`) |
| `CLAUDE_EFFORT`                 | current effort level on tool-use events                                                                                                                                                     |
| `CLAUDE_CODE_REMOTE`            | `"true"` in remote web environments; unset locally                                                                                                                                          |
| `CLAUDE_CODE_BRIDGE_SESSION_ID` | Remote Control session id while connected (v2.1.199+)                                                                                                                                       |
| `CLAUDE_PLUGIN_OPTION_<KEY>`    | a plugin option value, e.g. `CLAUDE_PLUGIN_OPTION_WEBHOOK_URL`                                                                                                                              |
| `OTEL_*`                        | **removed** from every subprocess Claude Code spawns                                                                                                                                        |

With `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, Claude Code also **strips credentials** from every subprocess it spawns,
hooks included alongside the Bash tool and stdio MCP servers: Anthropic and cloud-provider credentials, any other variable it
recognises as a credential, and credentials embedded in package-registry URLs. From v2.1.251 the scrub also removes
its own configuration-store pointers such as `CLAUDE_CONFIG_DIR`. A hook that needs a cloud token or has to find a
relocated config directory fails under the scrub even though the same command works in your shell; read the
secret from a file instead, or leave the scrub unset.

A hook process inherits the environment Claude Code was **launched** with. Exporting a variable inside a session's
Bash command does not reach the hooks.

Variables you set to change hook behaviour, rather than read from inside one:

| Variable                                             | Effect                                                                                                 |
|------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`            | overrides the shared `SessionEnd` budget explicitly, in milliseconds                                   |
| `CLAUDE_CODE_DISABLE_PERMISSION_PROMPT_NOTIFY_HOOKS` | set to `1` to turn the `permission_prompt` notification off in `canUseTool` sessions                   |
| `CLAUDE_CODE_DEBUG_LOG_LEVEL`                        | `verbose` adds matcher counts and query matching to the debug log                                      |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`                    | consecutive `Stop`/`SubagentStop` blocks allowed before the turn ends anyway (default 8, `0` disables) |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`                   | `1` strips credentials from hook, Bash and MCP subprocess environments (see above)                     |

`CLAUDE_CODE_USE_POWERSHELL_TOOL` is **not** required for a `"shell": "powershell"` hook, because hooks spawn
PowerShell directly rather than going through the PowerShell tool.
