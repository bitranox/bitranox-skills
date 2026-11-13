# Review checklist: the update-from-another-level refusal (step 3, "The level.")

Change: the "The level." bullet in step 3 said an add aimed at a non-owner level is refused with
`SlugCollision`, "which names the slug but not the level". The engine now refuses such an add
(sibling, ancestor or child of the owner) with `SlugOwnedElsewhere`, exit 2, writes nothing, and
names the owning level plus the update command. The bullet now says that, and says the suggested
`<slug>-2` is for a different fact only. The lead "each fails silently in its own direction" lost
its second half, since the level case is no longer silent.

- [x] Step 0b: `skill_decisions.py show meta-self-improve --kind rejected,removed --full` read; no
      entry covers this bullet, and no live rule anchors the old sentence.
- [x] Real behaviour executed: on a scratch tree with a root CLAUDE.md, `add` at level a, then the
      same `--slug` at sibling b, exit 2, output starting
      `! refused: slug 'probe-fact' is owned by another level of this tree: <tree>/a`, followed by
      the update command and the `probe-fact-2` suggestion; no file written at b.
- [x] RED (opus, pre-edit text from git): chose `--proj <owner>` from the refusal itself, and judged
      the text's description false ("The refusal names the level ... The excerpt says it does
      not").
- [x] GREEN (opus and haiku, new text): both chose `add --proj <tree>/a --slug probe-fact`, refused
      `probe-fact-2`, and quoted "rerun the same `add` with that level as `--proj`". 2 tiers, 2
      cells, plus one haiku re-run on the final text.
- [x] Gaps closed: the printed form and exit code (both GREEN arms, the class name is not printed)
      added; "printed as" changed to "on a line that starts", since the real line continues (haiku
      re-run).
- [x] Gaps declined, covered elsewhere in the skill: delta versus whole body (SKILL.md "An update
      re-sends what `add` requires, and stores every value it is given", step 3); the pinned case
      ("a pinned one is refused, see below", step 3); `<anchor>` and the engine path (the skill's
      storage spec, references/memory-backend.md). Which flags to carry over: "the same `add`" says
      it.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the bullet
      ("The slug.") still reads true.
- [x] Decisions: d-20261113-c78d0bc2
