# The parse snippet reads `.py` only; fenced Python is the pre-pass's

A paragraph after the hand-run snippet says it reads `.py` files only and names the
`fenced_python_syntax` check of `script_prepass.py` for Python fenced in Markdown.

- [x] Step 0b: the ledger holds no rejected or removed entry.
- [x] Premise check: the snippet globs `rglob("*.py")`. A parse of every `python`/`py` fence in
      four skill Markdown files found 4 blocks that fail `ast.parse`, none of which the snippet
      opens.
- [x] RED: text probe of the pre-edit section on haiku. What parses a fenced block in a
      SKILL.md: "Nothing in the excerpt names what does parse them, so that is NONE."
- [x] GREEN on opus and haiku with the edited section pasted: both named the
      `fenced_python_syntax` check and its three accepted shapes, quoting "That snippet reads
      `.py` files only."
- [x] Gaps declined: where `script_prepass.py` lives and how it is run (the section the new
      paragraph points at, "The pre-pass runs first", gives its home and `--room`); what the
      check does with other fence tags or shapes (the check's own summary line and tests, not
      this paragraph).
- [x] Decisions: d-20261116-40d1bb87
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN cells.
- [x] Width and fence check over the added lines printed nothing; the following paragraph
      ("Worth the same treatment") still reads on from the snippet.
