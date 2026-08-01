# skill-writer checklist - docs-md-table-formatting (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: rule 2's GOOD example showed 7/10 dashes for input whose widest cells are 4 and 5
      characters, contradicting rule 1 (width follows the widest cell). Ran the shipped
      `reformat_tables.reformat_file()` on the rule's own BAD input: it emits `| Name | Value |`
      over `|------|-------|`. The example is now exactly that output, with a line saying so.
- [x] Confirmed the RULE itself is right before changing the example: the hook path
      (`reformat_file`) does produce dashes touching pipes. `tablekit.render_table` renders a
      spaced variant, but that is not the function the hook runs.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
