# skill-writer checklist - meta-dream-tree (2026-11-09, batch cost and trim order)

Step 5 states the always-loaded cost of a batch of moves and excludes from a down-move any hook a
CLAUDE.md trim of this dream relies on. dream-passes: a fourth way a trim loses a rule, a down-move
in the same dream.

Decisions: none - additive rules; the one rejected entry (re-running ref_map after a dropped move) is a different step and stays as recorded

- [x] Step 0b `skill_decisions.py show meta-dream-tree --kind rejected,removed --full` read before the first edit.
- [x] RED, text check against the pre-edit files and every skill's Markdown: no wording for an aggregate byte cost of a batch, or for intersecting trims with down-moves.
- [x] The batch cost is summed over full pointer lines, not hooks. Measured on a real tree-top index: mean pointer line 490 bytes, mean hook 335 bytes, a 1.46 ratio, which matches the 1.5x under-estimate a mean hook length produced. Summing hooks would reproduce that error.
- [x] List intro updated from "Three ways" to "Four ways" for the added bullet; a repo-wide grep found no other citation of the count.
- [x] Not decided here: auto mode, where no propose-diff is shown. The text names the propose-diff only and leaves that case as it was.
- [x] GREEN: no subagent probe ran on this change; the evidence is the text check of the final files. The description is unchanged.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, fence balance unchanged.
- [x] Deployment: committed with one version bump, pushed with CI watched.
