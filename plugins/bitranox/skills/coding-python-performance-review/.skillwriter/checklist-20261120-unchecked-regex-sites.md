# skill-writer checklist - coding-python-performance-review (20261120, unchecked regex sites)

Change: `find_uncompiled_regex.py` lists each call site it could not check under its `Examined`
line as `  not checked: file:line - <kind>: <reason>` (kind `built at run time` or
`shape not modelled`). Step 4b says where those lines are, how an f-string, a `+` join and a
variable read, and what the rest of S is; the Step 5 format line names the new lines.

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing. The live rule
      d-20261119-1b8203f4 keeps all seven anchors; its decision ("the unchecked ones go to hand
      review") is extended, not reversed, so the new entry does not supersede it.
- [x] Claims in the new text executed: over the repo's tracked .py files the finder prints 111
      `not checked:` lines, all `built at run time`; an f-string site reads
      `built at run time: an f-string, assembled when the line runs`; a `+` join names its
      non-constant leaf (`re.escape(name)`); a parameter reads
      `pat is not a module-level name bound once to a string`. The 274 sites outside C, M and R
      were counted by site kind: all one-start, 0 that do not compile.
- [x] Tests: three new tests (the CLI listing with exact lines, the merged listing in file and
      line order, a not-modelled record) KILLED by mutation_arm `--revert` of the finder to its
      pre-change text; the whole skill test dir and the finder's doctests pass.
- [x] RED (opus, pre-edit 4b text, 3 questions): NONE for where the unchecked sites are, how an
      f-string is counted, and the line format; it read "hand review below" as possibly the next
      doc paragraph.
- [x] GREEN (opus and haiku, edited text, same 3 questions): both quoted the listing sentence, the
      f-string sentence and the line format. Gaps raised: the 274 sites outside C, M and R were
      unaccounted for (closed: a sentence naming the rest of S), f-strings counting in R was
      inferred (closed: "counts in R").
- [x] Re-probe (haiku, final text, the touched questions plus the 274): quoted the new sentences
      and closed the arithmetic. Declined: listing the patterns that do not compile (0 in this
      repo, and such a pattern raises re.error when its line runs); "4b undefined" and the cut-off
      excerpt (artifacts of the excerpt: 4b is the section's own heading).
- [x] Width and fence check over the added lines: one odd-backtick report on a line continuing a
      code span opened on the line before (unchanged structure); no line over 100 columns; no
      private host or path.

Decisions: d-20261120-f1de216f
