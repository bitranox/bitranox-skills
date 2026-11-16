# A refused relocate re-binds the fact; `add` refuses a frontmatter `topics:` line only

Two wording fixes: step 4b names what to do when the relocate is refused after the un-bind, and
step 2 scopes the `add` refusal to the frontmatter, as the engine applies it.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (an `off` behaviour
      for a 4b relocate) is not touched.
- [x] Premise checks: `memory_engine.py` `_body_topics_line` searches only the closed frontmatter
      block. Scratch tree: `add` with a prose `topics:` line exited 0, `add` with a frontmatter
      line exited 2 ("carries a frontmatter topics: line").
- [x] Command executed: on a scratch tree with a topic list, `set-topics --clear` and then
      `set-topics --topics python` each printed `set topics on 1 fact(s); 0 unchanged`, and the
      frontmatter line read `topics: [python]` again.
- [x] RED: text probe of the pre-edit text on haiku (quote or NONE). Refused relocate after the
      un-bind: "No next command is stated", no quote for a remedy.
- [x] GREEN on opus and haiku with the edited text pasted: both answered with the
      `set-topics ... --topics <the noted topics>` command and quoted "the fact is still in the
      source tree, un-bound"; both answered that a prose `topics:` line is not refused, by quote.
- [x] Gap closed: opus reported the list format of `--topics` as unstated; the sentence now says
      a comma-separated list (`set-topics --help`: "comma-separated tags from the tree's list").
- [x] Gaps declined: where the re-bound fact's lines at other levels come back (owned by
      meta-dream-tree, whose render places lines; this skill runs no render); what to do when
      the re-bind itself fails (the required output line is the stop, as for every engine call
      in this step); how frontmatter is delimited (the engine frames a body itself, and a copy
      is written without the line).
- [x] Decisions: d-20261116-1e4e9ef2, d-20261116-33a1c604
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN cells.
- [x] Width and fence check over the added lines printed nothing; the sentence after the
      insertion ("In `propose` the un-bind is part of the proposal") still refers to the un-bind.
