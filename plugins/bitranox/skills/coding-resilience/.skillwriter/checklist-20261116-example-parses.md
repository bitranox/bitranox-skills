# The cancel example's second alternative parses

The "or keep `await child`" alternative of the cancellation example is a whole
`try: await child` / `except asyncio.CancelledError:` statement, so the block is valid Python.

- [x] Step 0b: the ledger holds no rejected or removed entry.
- [x] RED: `ast.parse` (dedented) over every `python`/`py` fence of the pre-edit SKILL.md: 1
      failing block (a bare `except` with no `try`).
- [x] GREEN: the same parse over the edited file: 0 failing blocks.
- [x] The added lines match the prose above the block: "`try: await child except
      CancelledError:`" and "Re-raising when the cancel was aimed at you also works".
- [x] No subagent arm: the change adds no rule; the parser is the test of the one property
      changed.
- [x] Decisions: none - a syntax repair of one example; no rule added, removed or reworded
- [x] Width and fence check over the added lines printed nothing.
