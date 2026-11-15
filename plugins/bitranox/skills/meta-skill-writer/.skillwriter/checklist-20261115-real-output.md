# checklist - real tool output for claims and examples; self-contained probe excerpts

Two additions. "A quote-back proves the text is readable, never that it is true" now also covers
what a tool WRITES (run it and read the exact field before shipping a sentence about it) and
example values (copied from output produced in the session, never from recall). "A probe shown
only an excerpt..." now says to build the excerpt with every list or definition its passage
points at, or to ask no question that depends on it.

Decisions: d-20261115-c01146e6, d-20261115-b8538d01, d-20261115-6ac98f88

## RED

- [x] Skill decisions read first: two rejected entries (history file; probe hand-back from a
      subagent); neither touches this change.
- [x] Coverage probe on the pre-edit text, opus and haiku: example-value provenance answered NOT
      STATED on both tiers; building a self-contained excerpt NOT STATED on both; the tool-field
      question was answered only by "read the code", with a passing recipe left undecided.
- [x] Control: "decline with 'the tool already prints that line'" answered from the existing
      citation rule on both tiers in both arms.

## GREEN

- [x] Same questions on the edited text, opus and haiku: both quoted the new sentences verbatim
      and answered run-the-tool, copy-from-session-output, include-the-list.

## REFACTOR

- [x] Rejected, recorded as d-20261115-6ac98f88: a checklist test refusing every declined line
      without a citation. SKILL.md already requires it for a decline whose reason is a claim about
      the system ("cites its evidence in the same bullet: the `file:line` you read or the command
      you ran"), and both tiers quoted that line; other declines cannot be told apart by a check.
- [x] Declined (opus): "the decline's document is not named" - the paragraph before it names the
      review artifact.
- [x] Width and fence check over the added lines printed nothing.
