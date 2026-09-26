# skill-writer checklist - meta-skill-writer (2026-09-26, render-graphs contract, shim Windows scope)

Change: three doc syncs to shipped behaviour. (1) "Visualizing for your human partner" states that
`render-graphs.js` exits 1 when a diagram fails, that `--combine` refuses bare-statement blocks,
undirected `graph` blocks and node ids shared between blocks, and that separate mode renders them.
(2) "NO Code in Flowcharts" says a `dot` fence makes the tool fail (exit 1) rather than "report a
failure". (3) "Bundled scripts and hooks": the shim converts only the script's own path with
`cygpath`; Git Bash is the target Windows shell, the shim also runs hooks under Cygwin
best-effort, and WSL cannot be told apart from Linux by `uname -s`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference passages inside a technique skill. Test approach: quote-back retrieval
      arm (quote or NONE, haiku, inert `bitranox:baseline-probe`, passages pasted). Moved: Q1 exit
      code on a broken block, Q2 shared node id under `--combine`, Q3 undirected `graph` under
      `--combine`, Q4 Cygwin run or skip, Q5 WSL vs Linux via `uname -s`, Q7 whether a later
      `/regex/` argument is converted. Control: Q6 line endings of a shipped `.sh`.
- [x] Scope: prose in three sections; frontmatter, `name:` and description untouched.

## RED

- [x] Inherited coverage: `redcheck --corpus-cascade` on the worktree reported STRONG, on the
      shared terms apart, refuse, render, run-python, sharing - function words and tool names,
      not the lesson. Route taken regardless: the quote-back text check, which pasted context
      cannot contaminate.
- [x] RED, pre-change text: Q1 NONE ("reports a failure" names no exit code), Q2 NONE, Q3 NONE,
      Q4 "skips", quoting "not WSL or Cygwin", Q5 NONE, Q7 NONE and Q8 (script path) NONE on the
      old "converts POSIX paths" sentence. Control Q6 LF with its quote. Skill gaps: exit code
      unstated, duplicate-node and undirected behaviour unstated, scope of `cygpath` unstated.

## GREEN

- [x] Q1 1, Q2 refuses with exit 1, Q3 refuses, Q4 runs best-effort, Q5 no, Q7 no - each with a
      direct quote of the new text. Control Q6 unchanged with the same quote; nothing lost.
- [x] Skill gaps: one - Q8 (shared node ids WITHOUT `--combine`) answered NONE.

## REFACTOR

- [x] Q8 closed: the sentence now ends "separate mode renders every `digraph` block, shared node
      ids included". Re-tested by quote-back (haiku, inert probe): Q8 "does not refuse" and Q2
      "refuses with exit 1", both quoting the new sentence; no skill gaps reported.

## Quality

- [x] Every claim executed against the shipped tools with a control: a broken block exits 1 with
      "1 rendered, 1 failed" (a valid block exits 0 with "1 rendered, 0 failed"); two blocks sharing
      `start` exit 1 under `--combine` and 0 without it; an undirected `graph` block and a
      bare-statement block each exit 1 under `--combine` with a message naming the block. The shim
      runs a hook under a stubbed `uname -s` of `CYGWIN_NT-10.0-19045` and of `Linux` (exit 0,
      script ran) and degrades under `FreeBSD` (exit 0 with `--hook`, "unexpected shell").
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Security: prose only.
