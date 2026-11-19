# A bare metadata sub-key, and topics-show --json with no list

references/memory-backend.md states two engine behaviours changed with it: a bare `metadata:`
sub-key in an update's frame removes the stored one (`type:` excepted), and
`topics-show --json` in a tree with no topic list prints a JSON object.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (name-based
      misplacement signal) is not touched.
- [x] Behaviour pinned by tests in hooks/tests/test_memory_engine_update_partial_frame.py and
      test_memory_engine_topics_verbs.py, each RED on the pre-change engine.
- [x] RED: text probe of the pre-edit paragraph and row on haiku. A bare `skill:`: "probably
      removed, but the text does not state it for this case"; `topics-show --json` with no list:
      "the text does not say".
- [x] GREEN on opus and haiku with the edited text pasted: both quoted "a bare sub-key (`  skill:`
      with nothing below it) removes the stored one", answered that a bare `type:` keeps the
      stored kind, and gave `{"tagger": null, "topics": {}}` with exit 1.
- [x] Fix round: opus reported the row's output cell ("`no topic list in this tree` and exit 1
      when it has none") as unscoped and the stream as unstated; the cell now says
      "(without `--json`)" and the first cell "prints on stdout". Re-probe on haiku answered
      the JSON object alone on stdout, exit 1, sentence not printed, quoting both.
- [x] Gaps declined: a bare `skill:` against a body with no stored `skill:` (the paragraph's
      "A key that is stored bare and handed back bare stays" and the engine keeps the bare line;
      no case a reader acts on); the stream of the plain no-list sentence (unchanged by this edit,
      the row's other outputs name none either).
- [x] The table row was edited in place with its column widths kept (one changed line), so no
      other row of the table moved.
- [x] Decisions: d-20261119-8dfc4fc5 (the topics-show behaviour sits in a table row, which takes
      no anchor)
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN + 1 re-probe cell.
- [x] Width check over the added prose lines printed nothing past 100 columns.
