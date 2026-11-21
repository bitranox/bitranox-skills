# checklist - backlog_list returns an item's first line only

The tools paragraph and classification step 2 say that `backlog_list` reads each item's first line
only, so a field missing from its output (an `unranked` string, or an item with `size`, `open` and
`next` empty) is no evidence the item lacks it, and the item is read in the file before a field is
called missing or its state quoted.

Decisions: d-20261121-e534e0ad

## Premise check

- [x] `open_work.unranked_lines` and `open_work.list_items` run on a scratch OPEN-WORK.md holding a
      wrapped old-format item and a wrapped ranked item: `unranked` returned the first line alone,
      the ranked item came back with `size`, `open` and `next` all `None`.
- [x] `redcheck --corpus-cascade` on the lesson: verdict clean, so a behavioural RED is honest.

## RED (pre-edit text from `git show HEAD`, opus and haiku)

- [x] Both tiers told the user the unranked item has no `open:` and no `next:` field and needs a
      rewrite. Opus noted the text does not say whether `unranked` returns the whole entry.

## GREEN (edited text, opus and haiku)

- [x] Both tiers answered that the tool output cannot tell, and read the continuation lines in the
      file first, quoting "`backlog_list` reads each item's FIRST line only".

## REFACTOR

- [x] The sentence after the insertion began "They can sit in the deferred-tool list", which would
      re-bind to the continuation lines; reworded to "The tools can sit".
- [x] Width and fence check over the added lines: clean. ASCII scan and the history-phrase finder
      over the added lines: no hits.
- [x] Gap declined: how to convert an old-format unranked line into a ranked item (reported by both
      tiers in RED and GREEN). A conversion policy is a decision about the backlog format that no
      user ruling covers; the skill stays silent on it.
- [x] Gap declined: "the rank rules below are cut off" - excerpt-only; the rules are in this file,
      "**How rank is decided, in this order:**".
