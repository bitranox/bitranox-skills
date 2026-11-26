# skill-writer checklist - coding-consistency (2026-11-26, a breaking interface change is a departure)

On a user decision of 2026-11-26 rules 4 and 7 no longer require the old form of an interface
to keep working for callers outside the change. A breaking change to an interface the spec
names or outside code calls is a departure like any other, reviewed on its merit. The author's
statement names the callers it breaks, and the review lists a sound one for the owner with
those callers named.

Decisions: d-20261126-c4e2a42c

- [x] Receipt fresh, skill-writer loaded in the editing agent. Step 0b: the ledger was read
      before the edit; the entry this change supersedes is d-20261126-65f209bd.
      `skill_decisions.py check coding-consistency` reports 0 findings.
- [x] Not mirrored. The two language companions carry no such limit (grep: no hit).
- [x] What changed in the text: the last sentence of rule 4; rule 7 (a breaking change as a
      departure, the callers named in the fourth part, the cost stated); the end of the
      `DEPARTED (sound)` verdict; the paragraph after the finding bullets; the high rating
      (an outside caller that breaks on a change that is not sound); one rationalization row;
      the execution summary. The sentences "the existing form keeps working" and "a question
      for the interface's owner, whatever the reason" are gone.
- [x] RED (text check): the previous text reads "A departure that breaks a caller outside the
      change is `DISAGREE` whatever its ground." The rewritten test fails on that text and
      passes on this one.
- [x] GREEN, quote-back, haiku and opus (opus at default effort), headless with no tools, 7
      questions: both tiers answered alike and quoted the governing sentence. A required
      parameter added where the spec contradicts itself: allowed, stated in four parts with
      the callers named. Its review: `DEPARTED (sound)`, `stated`, unrated, listed for the
      owner with the callers. A spec-listed field renamed for taste with an outside reader:
      `DISAGREE`, high. Sound, unstated, callers unknown: `DEPARTED (sound)`, `silent`, the
      row says outside callers were not checked, plus a missing note. The old form need not
      keep working. The cost: an unseen caller breaks without the reason, a published library
      ships a broken release. Both runs ended in a `Skill gaps` section. The run was on the
      text before the one-clause change of the next item.
- [x] CLOSED (opus): the author names known and unchecked callers while the review row named
      one or the other; the row now names the callers where known and says whether callers
      outside the tree were checked.
- [x] DECLINED (reported to the user): the text gives no preference for a change that breaks
      nobody (an optional parameter with a default) over a breaking one that resolves the
      same ground. The decision allows the breaking change; whether a needlessly breaking one
      is still sound is the user's call.
- [x] DECLINED (reported to the user): nothing has to reach the callers that break (a
      changelog line, a version step); the statement goes to the spec's owner only.
- [x] DECLINED (judgement): the rating of an unsound interface change when no outside caller
      is known, and telling a contradiction from an incomplete spec; either gives a ground.
- [x] Width and fence check over the added lines: no prose line over 100 columns; every fence
      closed; ASCII only; the rationalization table's rows are all one width.
- [x] Description unchanged. Trigger map and catalogue regenerated and in sync.
- [x] Text test `test_a_breaking_interface_change_is_a_departure_that_names_the_callers_it_breaks`
      pins the new rule and the absence of the old limit.
