# skill-writer checklist - coding-python-performance-review (20261119, quadratic regex finder)

Change: `find_uncompiled_regex.py` gains a static check for the two quadratic-start shapes Step 4b
describes, reported in a second output section `# Quadratic Regex Starts`. Step 4b now says the
script reports them, how to read a hit, what to do before filing it, and what the finder does not
model; the tool table row and the Step 5 format line name the new section.

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing. The live rule
      d-20261117-c546f20d named this change as its reopen condition ("find_uncompiled_regex.py or
      another bundled scanner flags these shapes itself"); it is superseded by a new rule that
      keeps both of its anchors and adds the finder.
- [x] Premises checked by measurement: a known-quadratic positive per shape (class run before a
      suffix; newline start then blanks) grows past 24x from N to 8N in the test suite, its
      anchored fix and ordinary-regex controls stay under 16x. Repo scan: 30 hits, all 30 timed
      quadratic (48x to 69x, one cubic at 506x), none near 8x.
- [x] Claims in the new text executed: `/[^\s]+X` is not reported by the finder and times 59x on
      a run of `/` (the named hand-review case); the match-only skip is per file (the scan reads
      one file's loads), so a cross-module search is named for hand review.
- [x] RED: the pre-edit text said "`find_uncompiled_regex.py` does not look for it". A haiku
      quote-back over the pre-edit excerpt answered that no script finds the shape, so 40
      module-level patterns need a manual review, and that no verification step is given for a
      tool-reported hit.
- [x] GREEN round 1 (opus and haiku, 4 questions): both named the finder and the
      `# Quadratic Regex Starts` section, quoted the pre-filing timing and the severity rule, took
      the growth-test runs from the hit's `Runs that fail from every start:` line, and refused to
      call the unreported `/[^\s]+X` safe, quoting the hand-review sentence. Gaps raised and
      closed: the tool table row said "in functions" against "any scope" (row rewritten); no N
      was given (2,000 and 16,000 named); a hit timing near 8x had no rule (now a finder false
      positive to report); a match-only name searched from another module was uncovered (added to
      the hand-review list). Declined: a severity for a quadratic hit on bounded input off a hot
      path (a policy the user has not ruled on; raised as a question instead), and fixes for the
      hand-review shapes.
- [x] GREEN round 2 (haiku, final text, the touched sentences): did not clear a match-only name
      searched from another module (quoted the hand-review clause and timed b.py's call); dropped
      a 7.9x hit as a finder false positive, quoting the new sentence. Its remaining gap, the
      table row still saying "literal patterns", is closed by rewording the row to "Flag literal
      re calls; any re pattern with quadratic start".
- [x] Width and fence check over the added lines printed nothing; no non-ASCII added.

Superseded: d-20261117-c546f20d, whose reopen condition this change meets.

Decisions: d-20261119-a189b19d
