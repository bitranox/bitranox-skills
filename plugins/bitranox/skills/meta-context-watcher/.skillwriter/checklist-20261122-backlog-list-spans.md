# checklist - backlog_list returns each item with its wrapped lines

`open_work.py` now reads an item as a span: the item line plus every following line up to the
first blank line, heading, fence, checkbox line, or list marker no deeper than the item's indent.
The tools paragraph and classification step 2 said the tool reads the first line only; both now
describe the span, and keep the read-the-file rule for a field written past the end of the span.

Decisions: d-20261122-3a083094

## Premise check

- [x] The fixed parser on the probe fixture: item 20 (fields on two indented continuation lines)
      returns `size` "2 sweeps", `open` "waiting on CI", `next` "rerun the prune"; item 30 (an
      indented `| next:` after a blank line) returns `next` None. A whitespace-only line counts as
      blank (`_span_end` tests `line.strip()`), and a deeper checkbox line ends an item
      (`test_an_indented_ranked_checkbox_stays_an_item_of_its_own`).

## RED (pre-edit text, opus and haiku)

- [x] Both tiers answered that the tool returns no `size` for item 20, citing "`backlog_list`
      reads each item's FIRST line only", which the fixed tool contradicts. Haiku also refused to
      trust the tool's `open` for item 20 on the same sentence. Both reported the text silent on a
      blank line inside an item.

## GREEN (edited text, opus and haiku)

- [x] Both tiers: item 20's `size` is "2 sweeps", quoting "`backlog_list` returns each item with
      its wrapped lines joined to it, fields written on those lines included"; item 30 has a next
      step and the file must be read, quoting "a field missing from the tool's output is no
      evidence the item lacks it".

## REFACTOR

- [x] Gap closed: opus reported that "An item runs until a blank line" contradicted "after a blank
      line inside the item". Reworded to separate where the TOOL ends an item from where its
      author wrote fields. Re-probe on the final text, opus and haiku, same three questions plus
      "does the text contradict itself about where an item ends": both NONE, no new undecided gap.
- [x] Width and fence check over the added lines: clean. ASCII scan: no hits. The sentence after
      the insertion ("The tools can sit in the deferred-tool list") keeps its referent; reflowed
      onto the last line of the new text.
- [x] Gap declined: how far to read an item in the file. Where an author's entry ends is a reading
      judgement on the file itself; the skill already says to read it there.
- [x] Gap declined: whether `backlog_list` reads the file live. It reads `OPEN-WORK.md` on every
      call (`open_work.list_items`); freshness of an item's own wording is step 2's last-segment
      rule plus its live check, unchanged.
- [x] Gap declined: the elided middle of step 2 ("Quote that last segment as the item's state
      ...") - excerpt-only; the full step is in this file under "Read each candidate's WHOLE
      entry".
- [x] Gap declined: how the wrapped lines are joined. The fields are what the reader uses; the
      separator (one space) does not change any answer.
