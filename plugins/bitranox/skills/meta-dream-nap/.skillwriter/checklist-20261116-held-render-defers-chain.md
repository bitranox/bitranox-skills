# A held-back render defers the cwd's own lines too

Step 4b says what happens to the rest of the chain when a pending arrival at the tree top keeps
the nap from running the real render in propose mode and under `off`.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (reconcile verify
      step) is not touched.
- [x] Premise check: the step's only writer is the one `render-topics --scope chain` call, and
      the text says "do not run the real render"; nothing said what that means for the levels
      below the top.
- [x] RED: text probe of the pre-edit step on haiku. Dry run `<anchor>: +1 added` and
      `<cwd level>: +3 added`: it answered that the 3 lines are not written, and listed as a gap
      that this "is my reading, not the text's"; it placed them in the report, not the deferred
      list.
- [x] GREEN on opus and haiku with the edited step pasted: both answered that the 3 lines wait
      for the tree dream's render and go in the deferred list, quoting "With the real render not
      run, nothing of this step's placement is written".
- [x] Gaps declined: what the deferred list is (step 6 names it: an explicit "deferred to the
      full dream" list in the report); how a line's cost is computed (dream-core.md, Mode: the
      UTF-8 length of the pointer line plus the newline); "a new project gets the rules of its
      stack at its first nap" against the deferral (the same paragraph carries "unless the tree
      top's line stops you (next paragraph)").
- [x] Decisions: d-20261116-51a92046
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN cells.
- [x] Width and fence check over the added lines printed nothing; step 5 follows the insertion
      and holds no back-reference.
