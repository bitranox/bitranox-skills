# `add` refuses a frontmatter `topics:` line only

The "Topics are never written by hand" paragraph scopes the refusal to the frontmatter and says
what a `topics:` line in the prose is.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (name-based
      misplacement signal) is not touched.
- [x] Premise check: `memory_engine.py` `_body_topics_line` searches only the closed frontmatter
      block. Scratch tree: `add` with a prose `topics:` line exited 0 and stored the fact; `add`
      with a frontmatter line exited 2 ("carries a frontmatter topics: line").
- [x] RED: text probe of the pre-edit paragraph on haiku. A new fact whose prose has a line
      starting `topics: `: answered "Yes, by the literal text", the opposite of what the engine
      does.
- [x] GREEN on opus and haiku with the edited paragraph pasted: both answered no and quoted
      "A `topics:` line in the prose below the frontmatter is ordinary text: `add` stores it and
      it tags nothing."
- [x] Gaps declined: how the frontmatter block is delimited (a capture writes a bare body and
      `add` frames it, `memory_engine.py` `_framed_body`); what `add` does with `topics: []`
      (it is a frontmatter `topics:` line, so the stated rule covers it).
- [x] Decisions: d-20261116-27cc4514
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN cells.
- [x] Width and fence check over the added lines printed nothing; the next paragraph ("An update
      re-sends what `add` requires") holds no back-reference to this one.
