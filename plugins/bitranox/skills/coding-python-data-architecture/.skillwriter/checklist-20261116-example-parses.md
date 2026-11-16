# The "Anti-Patterns to Eliminate" example parses

The `if user.status == "active":` line of the anti-pattern block has a body (`...`), so the
block is valid Python.

- [x] Step 0b: the ledger holds no rejected or removed entry.
- [x] RED: `ast.parse` over every `python`/`py` fence of the pre-edit SKILL.md: 1 failing block
      ("expected an indented block after 'if' statement").
- [x] GREEN: the same parse over the edited file: 0 failing blocks.
- [x] No subagent arm: the change adds no rule and no wording a reader acts on; the parser is
      the test of the one property changed.
- [x] Decisions: none - a syntax repair of one example; no rule added, removed or reworded
- [x] Width and fence check over the added line printed nothing.
