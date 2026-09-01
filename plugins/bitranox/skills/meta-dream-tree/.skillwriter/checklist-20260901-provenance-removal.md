# skill-writer checklist - meta-dream-tree (de-double no longer keys on bx:src)

Change: one clause in step 3b. The tier de-double said a native entry could be recognised as
already curated "by `bx:src` provenance or title/hook match". Provenance is no longer rendered on
a pointer line, so the first half of that OR names data the step cannot see. The clause is removed
and the title/hook match, which is what has been doing the work, is stated alone.

## PLAN

- [x] Skill type: technique (a procedure step with a recognition rule).
- [x] Test approach: coverage check against the skill FILE plus a ground-truth check of the data
      the step reads. Recorded here as the chosen route, because the behavioural arm for this
      clause would be testing the engine's render output rather than the skill's teaching.
- [x] Scope: one clause; the invocation it references is owned by meta-self-improve's checklist.

## RED

- [x] The step reads pointer BLOCKS (step 3 loads "every level's pointer block under the anchor"),
      and a rendered pointer line is now `- [T](mem:s) - h <!-- bx:pin -->`. The token the clause
      tells the reader to match on is absent from the text the step loads.
- [x] The write side never produced what the read side needed even before the removal: the recorded
      keys were batch labels rather than the native slugs the same sentence tells the reader to
      merge, so the documented lookup could not match its own data.

## GREEN

- [x] The remaining rule, title/hook match, is checked against the file: it is stated without a
      dependency on provenance and needs no data beyond the pointer line's title and hook, both of
      which the step already loads.
- [x] `grep -c bx:src` over the corrected SKILL.md returns 0.

## REFACTOR

- [x] No new rationalisation is introduced: the clause is narrowed, not replaced, so there is no
      new instruction for a reader to work around.
- [x] Undecided gap list is empty.

## Quality

- [x] Present tense, no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added by this change.
- [x] Frontmatter untouched: no `name` or `description` change, so no routing keyword moved.
