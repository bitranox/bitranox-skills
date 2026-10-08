# Memory and backlog as model-callable tools (a Claude Code mod) - design

OPEN-WORK [17]. The user picked this use of Claude Code mods on 2026-10-08, over a status band or
pane, and then chose v1 scope, packaging, architecture and tool inputs one decision at a time.

## Decisions

| Decision          | Chosen                                                            | Rejected, and why                                                                                                            |
|-------------------|-------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| v1 scope          | backlog tools plus `memory_add` and `contrib_add`                 | backlog only (leaves memory for later); memory only (wraps what works, leaves the one area with no write path untouched)     |
| Packaging         | inside the `bitranox` plugin (`hooks/hooks.json` gains `modules`) | a separate opt-in plugin (second install, cross-plugin script lookup)                                                        |
| Where logic lives | Python, behind one JSON bridge; TypeScript is a thin adapter      | backlog logic in TypeScript (the OPEN-WORK.md rules would live in two languages, `session-start.py` already parses the file) |
| Backlog rank      | required on `backlog_add`; the tool enforces uniqueness only      | the tool picks a rank (ignores size and deferral, drifts from the written ranking rules)                                     |

## What was measured before deciding

- Mods API (Claude Code 2.1.290, bundled `plugin-authoring` types): `$.tool.register({name,
  description, inputSchema})` lists a tool as `mcp__<plugin>__<name>`; a `tool.call` hook on that
  name answers it with `{ result }` (a `{ text }` answer is refused as the wrong shape).
  `$.process.run(argv, {cwd, env, stdin, timeoutMs})` runs a host command with no shell, 30 s
  default timeout, 4 MiB per stream. `$.plugin.root` is the plugin's folder.
- One `hooks/hooks.json` holding both the classic `hooks` map and `modules` works on 2.1.290: a
  headless `--plugin-dir` probe ran the classic SessionStart command AND answered a registered
  tool from the module.
- Nothing shipped writes `OPEN-WORK.md` today (grep over every non-test `.py` under `plugins/`:
  only readers and message strings).
- `memory_engine.add_or_update_entry(proj, title, hook, body, type_, ...)` takes strings and
  raises typed errors (`HookTooLong`, `EmptyBody`, `PinnedEntry`, `InvalidSlug`,
  `SlugCollision`); `contrib_queue add` goes through `self_improve_signals.add_contribution`.

Not measured: how a Claude Code release WITHOUT mods support treats the `modules` key. That is
release gate 1 below.

## Architecture

```
model --tool_use--> mcp__bitranox__<tool>
  hooks/mods/register.ts   tool.call hook: JSON {tool, input} on stdin
    $.process.run(["bash", <root>/hooks/run-python.sh, <root>/hooks/mod_bridge.py], {stdin, cwd})
      hooks/mod_bridge.py  dispatch in-process, print one envelope, exit 0 / 1 / 2
        hooks/open_work.py        backlog_list / backlog_add / backlog_close
        hooks/memory_engine.py    memory_add (the CLI add branch, extracted so both share it)
        self_improve_signals      contrib_add
  <- { result: envelope } ; a non-zero exit or timeout becomes a tool error
```

- `run-python.sh` is reused so the bridge gets the same interpreter probe, UTF-8 forcing and Git
  Bash handling as every classic hook.
- The `tool.call` hooks carry a `.catch` so a crash fails the call loudly instead of passing it.
- The CLI `add` branch of `memory_engine.py` is extracted into a function the CLI and the bridge
  both call, so warnings and validation cannot drift between the two entry points.

## Tools

| Tool            | Input (`*` required)                                                                                                                                | `data` on success                                                 |
|-----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `backlog_list`  | `state` (`open`, `closed`, `all`; default `open`)                                                                                                   | list of `{rank, raised, origin, what, size, open, next, closed?}` |
| `backlog_add`   | `rank*`, `origin*` (`USER`, `FOUND`), `what*`, `size*`, `open*`, `next*`, `raised` (`YYYY-MM-DD`, `YYYY-MM-DD?`, `unknown`; default today plus `?`) | `{rank, line}`                                                    |
| `backlog_close` | `rank*`, `reason*`                                                                                                                                  | `{rank, line}`                                                    |
| `memory_add`    | `title*`, `hook*`, `body*`, `level` (dir; default the session cwd), `type`, `slug`                                                                  | `{slug, level, action: created or updated, warnings}`             |
| `contrib_add`   | `what*`, `target*` (one line, e.g. `hook` or `skill:<name>`, as the live queue spells it), `why*`                                                   | `{queued, reason?}`                                               |

Envelope: `{ok: true, tool, data}` or `{ok: false, tool, error: {kind, message}}`, where `kind`
names the typed exception (`RankTaken`, `UnknownRank`, `AlreadyClosed`, `MalformedField`,
`HookTooLong`, `SlugCollision`, ...). Exit 0 on success, 1 on a refusal, 2 when the bridge could
not run (bad JSON, unknown tool).

Backlog rules the tool enforces (and no others):

- the file is `OPEN-WORK.md` at the git top level of the session cwd; `backlog_add` creates it
  with the standard header when absent, `backlog_list` returns an empty list with a note;
- a rank is a positive integer free over EVERY line, closed ones included; a refusal names the
  nearest free tens as suggestions. Tens are the convention, not a rule the tool enforces: the
  live backlog measured 2026-10-08 holds 5, 7, 12-19 and 121 beside the tens, and already has
  three ranks on two lines each (14, 16, 95);
- the file is not sorted by rank (same measurement), so "rank order" means: the new line goes
  directly after the item whose rank is the largest one below it, or before the first item when
  none is smaller; the file grows by exactly one line (asserted before writing);
- a rank that labels more than one OPEN line cannot be closed by number (`AmbiguousRank`), since
  the tool cannot tell which one is meant;
- closing writes `- [x]` plus `| closed: <reason>`; the line is never deleted;
- a missing `raised` is today's date with `?`, never an inferred date.

Ranking itself (USER over FOUND, deferral, size) stays the model's judgment.

## Testing

- pytest (CI's dependency set), RED first:
  - `open_work.py`: round-trip every line of the live `OPEN-WORK.md` without loss; rank held by a
    closed line refused; order and boundary of insertion; +1 line delta; close keeps the line;
    malformed fields refused; missing file created with the header.
  - `mod_bridge.py`: each tool against a real temp git repo and memory tree, no monkeypatching of
    our own code; typed error to `kind`; garbage stdin gives an `ok: false` envelope and exit 2.
- `claude plugin test`: all five tools registered; a call reaches `$.process.run` and the envelope
  is relayed (against a stub script, not the real engine).
- Live e2e: headless `claude -p --plugin-dir plugins/bitranox` on haiku calls `backlog_add` then
  `backlog_list` in a scratch repo; pass means the line is in the file.

## Release gates (either failing goes back to the user before shipping)

1. Older CLI: an earlier Claude Code without mods support, installed into the scratchpad, still
   fires the classic bitranox hooks with the `modules` key present.
2. Windows: the bridge runs through `run-python.sh` on the Windows dev VM (Git Bash).

Then a minor bump with a CHANGELOG entry and a `docs/reference.md` row, `repo-gate.py --ci` green,
CI watched after the push, [17] closed.

## Out of scope

`backlog_rerank`, memory move/retitle tools, the backlog band or pane (still an option later).
