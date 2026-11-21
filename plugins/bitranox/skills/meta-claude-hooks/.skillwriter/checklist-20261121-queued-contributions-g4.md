# checklist - mod tools get no tool events; mod subprocess session id; liveness twin in tests

- configuration.md, "Matching MCP tools": a tool a plugin mod registers gets no `PreToolUse` or
  `PostToolUse` event, so a guard that must cover it applies its rule inside the mod; with a
  re-probe recipe. SKILL.md question 3 points at it.
- io-contract.md: a `$.process.run` subprocess has no `CLAUDE_CODE_SESSION_ID`; pass
  `$.session.id()` explicitly and test with the variable unset.
- authoring.md: quote the `as_posix()` path in a Bash-tool test command, and pair every pass test
  of a file-reading guard with a refusal twin built the same way.

Decisions: d-20261121-3bc6024d, d-20261121-161e264a, d-20261121-4b941997

## Premise check

- [x] Headless probe on CLI 2.1.330 with a scratch settings file, matcher
      `Bash|mcp__bitranox__backlog_list|mcp__.*` on PreToolUse and PostToolUse: the hook log holds
      Pre and Post for Bash only; the probe session's transcript shows `mcp__bitranox__backlog_list`
      called and returning `ok: true` in the same turn.
- [x] `/proc/<pid>/environ` of the `claude` process, names only: no `CLAUDE_CODE_SESSION_ID`,
      `HOME` present (control); the Bash-tool child has the variable.
- [x] `shlex.split` of `git commit -F ` plus an unquoted Windows `str(path)` with a space dropped
      the backslashes and split the path; the quoted `as_posix()` form parsed to one intact token.
- [x] `hookdoc_stamp.py check --json`: verdict COSMETIC, cached false, content 023796a78c9d /
      84bb31e34501, structure 1892797befc9 / 931ce1f43d8a, cli_ahead_of_docs true.
- [x] `redcheck --corpus-cascade` on both lessons: clean.

## RED (pre-edit text from `git show HEAD`, opus and haiku)

- [x] Mod tool under a `mcp__myplugin__.*` matcher: both tiers NOT STATED; neither said it gets no
      event, so a hook-only design would ship.
- [x] Bridge reading the session variable: both tiers NOT STATED.
- [x] Test pair: both reasoned `as_posix()` from the text and a liveness pair themselves; the text
      was silent on the pass twin and on quoting.

## GREEN (edited text, opus and haiku)

- [x] Both tiers quoted "gets no `PreToolUse` or `PostToolUse` event at all", the
      `$.session.id()` sentence and the liveness-twin sentence, and drew the right conclusions.

## REFACTOR

- [x] Both tiers read the session-lookup sentence (`reads ""`) as contradicting a `KeyError` from
      `os.environ[...]`; reworded to name both outcomes. Haiku read "the same command and path" as
      "merge the two tests"; reworded to "builds the command and the path the same way ... (two
      test functions are fine)". Quote-back re-probe on the final text, haiku and opus: both quoted
      the fixed sentences, concluded `KeyError` and "no merge needed"; no new undecided gap.
- [x] Added paragraphs reflowed to 100 columns; width and fence check over the added lines clean.
      ASCII scan and history-phrase finder: no hits.
- [x] Gap declined: "a `Write` matcher is not stated" - excerpt-only; configuration.md line 103
      lists `Bash`, `Edit|Write`, `mcp__.*` for the tool events.
- [x] Gap declined: stdin field versus env entry for the id, and how the bridge turns the id into a
      transcript path - left to the mod's author; the text names both carriers.
- [x] Gap declined: what `$.session.id()` returns inside a subagent - unmeasured; no text added.
