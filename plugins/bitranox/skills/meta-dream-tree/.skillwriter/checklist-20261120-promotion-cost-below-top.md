# skill-writer checklist - meta-dream-tree (promotion cost below a tree top)

- [x] Change: references/dream-core.md's report contract lists a promotion to a common ancestor below the top as applied, by slug, with its level and its cost there.
- [x] Decisions: d-20261120-78a223b8
- [x] Step 0b: `skill_decisions.py show meta-dream-tree` (all entries, and `--kind rejected,removed --full`)
      read before the first edit; no rejected or removed entry concerns report costs, and the
      live cost entries (promotion to a tree top, re-home to the top) keep their anchors.
- [x] RED: opus and haiku text probes on the pre-edit text of both files answered NONE for what
      the report lists for a promotion to /work/services below the top /work, and each named the
      missing below-top cost a gap.
- [x] GREEN: opus and haiku probes on the edited text quoted the new sentences, with the level
      and the grep, for the same scenario; the gaps they still raised concern propose-mode
      promotions and a corroboration condition at the top, both outside this change.
- [x] Mechanism executed: the cost command is the same `grep -F '(mem:<slug>)' <file> | wc -c`
      that d-20261119-cc073a1a measured, pointed at the level's CLAUDE.local.md.
- [x] Contract test test_a_promotion_below_the_tree_top_is_reported_with_its_level_and_cost in
      hooks/tests/test_dream_skill_contracts.py: KILLED by reverting either file to the pre-edit
      text (mutation_arm --revert), passes on the edited text.
- [x] Width and fence check over the added lines printed nothing; description unchanged.
- [x] Present tense, no history lines, no private hosts, paths or personal data.
