# skill-writer checklist - compuse-toolbox (2026-09-04, anchor_edit insert direction)

Change: the `anchor_edit` row states the insert DIRECTION. The usage cell shows `--before` instead
of `--after`, and the description gains a clause saying `insert` takes `--after|--before` with
`--after` as the DEFAULT, so an omitted direction lands the text after the anchor. No frontmatter
change; no other row touched.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Skill type: REFERENCE. The row is an index entry, so the tests that apply are whether what it
      SAYS is true of the shipped tool and whether a reader can act on it - not whether it changes
      a decision.
- [x] ACCURACY, checked against BEHAVIOUR rather than against the argparse source: on a three-line
      fixture anchored to its middle line, `insert` with no direction produced `A / B / NEW / C`,
      and `insert --before` produced `A / NEW / B / C`. So the default is `--after` and the row's
      claim holds. Reading `default=True` in the parser agrees, but the run is the evidence.
- [x] The old cell was not merely incomplete, it was misleading: showing `--after` in a usage
      example reads as a choice being made, which is what a reader copies. The new cell shows the
      flag that has to be typed to change the outcome.
- [x] Behavioural RED not run, and the reason is recorded rather than worked around:
      `redcheck --corpus-cascade` reports STRONG inherited coverage for this lesson on any machine
      whose memory store carries the anchor-an-insert-on-an-item-boundary entry, so an agent
      dispatched there answers from that entry, not from this row. The evidence taken instead is
      the accuracy check above plus a text check of the artifact, which inherited context cannot
      fake.
- [x] Failure mode this closes, and its cost: an insert aimed at the opening line of a block, with
      the direction omitted, lands one line INSIDE that block and splits it. The tool reports a
      clean line delta either way, so nothing surfaces it.
- [x] No frontmatter change: the committed diff touches the one table row only, `name:` and
      `description:` unchanged (0 frontmatter lines in `git diff`), so no routing keyword moved.
- [x] Scripts unchanged by this entry, so their tests are unaffected; the suite is green at 4700
      passed via `repo-gate.py --ci`.
- [x] Present tense, no session narrative, no machine-specific address or path added.
