# skill-writer checklist - meta-dream-tree (add the local skill/hook audit pass)

Change: step 9's behavioral-pass catalog gains one entry, "local skill/hook audit", and
`references/dream-passes.md` gains the matching section. The pass covers the PROJECT half only -
this tree's own `.claude/skills`, with `--no-personal`.

## Scope
- [x] Wiring change only. The procedure it points at is `bitranox:meta-audit-local-skills-and-hooks`,
      reviewed under its own checklist; nothing about ownership or the checks is restated here.
- [x] Single source confirmed: neither call site repeats the ownership rule body. Verified by
      grepping both for `claude-plugin` and `REPORT ONLY` - zero hits in each.

## RED
- [x] Before the change the catalog had no pass covering a tree's own `.claude/skills`, so the
      13 project skills in one tree on this machine had never been reviewed once, and 12 of 13
      carried no tests. Absence of the pass is the failing condition.

## GREEN - verified from behaviour, not from the text
- [x] A subagent given only `SKILL.md` and `references/dream-passes.md`, asked to run step 9 for
      one tree, listed the new pass in the correct catalog position.
- [x] Asked whether the pass examines `~/.claude/skills`, it answered no and quoted the governing
      line ("the personal `~/.claude` half is machine-global and belongs to the deep crosstree
      dream, not here").
- [x] Offered a `find`-based target list as a shortcut, it refused and quoted the governing line
      ("do not re-derive the target list with a `find`, which is how a tool repo's mirrored twin
      gets edited"). This is the failure mode the pass exists to prevent.

## REFACTOR
- [x] Gap reported: the pass named the skill but not how to invoke it, and the reply invented a
      command line treating the skill name as an executable. CLOSED: the pass now says to invoke
      the SKILL, and that its `audit_local.py` is what takes `--root` and `--no-personal`.
- [x] Undecided gap list is empty.

## Quality
- [x] Trigger-first pass, ending in an explicit no-op condition, matching the catalog's convention.
- [x] Findings follow this project's dream mode, stated in the pass.
- [x] No narrative, no provenance, no machine paths beyond the reserved generic forms.
- [x] ASCII only.
- [x] Frontmatter untouched, so the CSO description is unchanged and needs no re-review.
