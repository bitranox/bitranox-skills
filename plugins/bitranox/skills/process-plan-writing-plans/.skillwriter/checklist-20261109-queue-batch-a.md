# skill-writer checklist - process-plan-writing-plans (20261109, gate config, floors, tests that show their claim)

Queue entries: A19, A20, A21, A22, A23, A24, A25, A28.

- [x] Decisions: none - additive rules from queued items; no ledger rule was reversed or removed

- [x] Step 0b: `show --kind rejected,removed --full` read for this skill; no entry touched.
- [x] RED by text check against the pre-edit text (`git show HEAD:`): every distinctive phrase of
      the added rules was absent there (listed below). No behavioural RED: the session's always-
      loaded memory index states several of these lessons, so a probe could not fail honestly; the
      coverage check against the skill file is the evidence.
- [x] Phrases checked: "gate configuration", "names what sets it", "must be public there", "unifies
      the paths", "continue-on-collection-errors", "replaced by a pointer", "distinct increasing
      deltas", "argument --max-rows".
- [x] GREEN: quote-back probe over the pasted new text, 27 scenarios covering every added rule,
      `opus` at effort `medium` and `haiku`, 2 cells. Both tiers answered every scenario with a
      direct quote of the governing sentence, none NONE. Two scope controls (a different defect
      class; a child process that needs no version-specific dependency) were both correctly outside
      the new rules, so the rules do not over-trigger.
- [x] A21, A22, A23 are merged into Self-Review item 12. Executed: pytest stops at a collection
      error in one of two files (rc 2, no result for the other), `--continue-on-collection-errors`
      reports both (rc 1, 1 failed, 1 error); argparse exits 2 on an unknown option.
- [x] Gaps declined: a word-boundary rename can hit unrelated same-named privates (the rename says
      across callers, a code-review matter); other CLI parsers format the message differently (the
      argparse string is an example).
- [x] Width and fence check over the added lines printed nothing new beyond this file's own long
      lines; ASCII only; frontmatter parses with a YAML loader and its description is under 1024.
