# skill-writer checklist - coding-python-textual (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled. Ships with plugin 5.126.0.

- [x] WRONG: `examples/guide/styles/border_title.py` did not parse - `"by Frank Herbert, in "Dune""`
      has unescaped nested quotes. Confirmed with `ast.parse` raising SyntaxError, fixed by
      switching the outer quoting, and the identical line in `guide/styles.md` fixed with it.
- [x] Generalised the check rather than stopping at the one report: `ast.parse` over EVERY shipped
      `.py` in the catalogue now reports 0 broken files, so that defect class is cleared across all
      67 skills rather than just the one a reviewer happened to reach.
- [x] Remaining findings REPORTED, not applied. This skill vendors upstream Textual documentation,
      and rewriting vendored pages makes the copy disagree with its source: a `CSS_PATH` pointing
      at a `.tcss` that lives in a sibling example directory, a bare dotted-path link in
      `tutorial.md`, and an undated "latest version" claim in a how-to. Each is upstream's to fix.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file before acting; every executable claim re-run rather
      than taken from the report.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
