# skill-writer checklist - compuse-toolbox (2026-11-26, full tool entries moved to references/tools.md)

Decisions: d-20261126-6b023d25

- [x] Step 0b: `show --kind rejected,removed --full` printed three rejected entries (a code
      decisions ledger, ci_wait's CI_RC= line, gate's --name help text); none is reversed here.
      Every live `rule` anchor is still in the skill directory (the gate reads SKILL.md and
      references/ together).
- [x] Move verbatim by script: each row's middle cell went to `references/tools.md` under
      `## `name``, with `\|` unescaped to `|` (outside a table a backslash would print); the
      Invoke cell stays in SKILL.md unchanged, so the factedit registration test that reads the
      launch column still covers every row.
- [x] Nothing lost: every non-blank line of the pre-split SKILL.md is in SKILL.md or, as a cell,
      in the page; the one expected miss is the reworded table header, which also proves the
      check can fire. No "above"/"below" in the moved text points across the page boundary.
- [x] The page opens with a line pointing back to `../SKILL.md`; SKILL.md lists the page first
      in its `references/` list, with when to read an entry.
- [x] Test: `tests/test_skill_tools_index.py` requires the table's tools and the page's headings
      to be the same list in the same order; RED on a renamed heading, GREEN restored.
- [x] Routing, SKILL.md index alone, opus and haiku, 10 chores (2 controls): both missed the API
      rate limit and the re-run attempt for `ci_wait`, and both matched `winlog` only by
      inference (no Tee-Object). After adding those words to three summaries both tiers routed
      all three and kept the control at NONE.
- [x] Tokens per invocation (opus, `claude -p` request usage minus an empty baseline): 34.1k
      before, 20.9k after; `references/tools.md` 15.7k, paid only when read.
- [x] Tiers: opus and haiku for routing (the index is read by both); no rule text changed, so no
      RED/GREEN on behaviour beyond routing.
