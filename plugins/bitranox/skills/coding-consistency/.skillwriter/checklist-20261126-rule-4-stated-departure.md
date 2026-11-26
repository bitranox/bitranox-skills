# skill-writer checklist - coding-consistency (2026-11-26, rule 4 as a stated departure)

Writing rule 4 changes on a user decision of 2026-11-26: an author MAY change a point the spec
fixes when they judge it sensible, above all where the spec is unclear, incomplete or
contradicts itself, and states it as a deliberate departure in the commit message and in the
hand-over, in four parts (what the spec says, what the code does instead, why, what a user or
caller sees differently). Silent, or with a reason that does not hold against the spec text, it
stays a defect. The review side follows: a changed fixed point is `DEPARTED (stated)` when the
statement is complete and its reason holds, listed unrated under "departures for the owner's
decision", and `DISAGREE` otherwise.

Decisions: d-20261126-1d9f8d21, d-20261126-65f209bd

- [x] Receipt fresh, skill-writer loaded in the editing agent. Step 0b before the edit:
      `skill_decisions.py show coding-consistency --full` read; no rejected or removed entry
      speaks about fixed points, and the strict wording of rule 4 had no ledger entry, so the
      new `rule` entry supersedes nothing.
- [x] Not mirrored: the skill ships only from this marketplace.
- [x] What changed in the text: rule 4; rule 7 (a changed listed interface is a rule-4
      departure, and an interface outside callers use keeps its existing form working); a
      fifth verdict `DEPARTED (stated)` with the reviewer's check of the reason; the heading
      of review step 3; the paragraph after the finding bullets; the rating sentences; two new
      rows of the rationalization table; the execution summary; two clauses of the
      description.
- [x] Narrower than the decision's wording, on one kind of fixed point: a departure never
      covers breaking a caller outside the change, because the statement reaches the reviewer
      and the spec's owner and not that caller. Recorded as its own entry
      (d-20261126-65f209bd, tier argued) for the user to confirm or reverse.
- [x] Companions: neither `coding-python-consistency` nor `coding-rust-consistency` restates
      rule 4 (grep for "rule 4", "fixed point", "as written", "spec's owner", "departure",
      "question for": no hit); unchanged.

## RED (text check of the pre-edit file)

- [x] The lesson is a user decision that reverses the shipped rule, so the evidence is the
      pre-edit text, not a behavioural arm: rule 4 at HEAD reads "the code still does what the
      spec says and the conflict goes to the spec's owner as a question", and the file has no
      hit for `DEPARTED`. The three new text tests fail on a tree holding the HEAD skill text
      and pass on the edited one.

## GREEN on the new text (implementer scenario, 2 cells)

- [x] Probe set-up: headless, no tools, a fresh empty working directory, the first assistant
      text block; the prompt carries this SKILL.md and the Python companion. Scenario: a panel
      design whose line 3 fixes the response window at the last 50 tickets, whose alert line
      5.1 says "the response window (the last 30 closed, counted tickets)" and whose line 5.2
      says the alert uses the figure the panel shows; files are handed back without a commit,
      and the design's owner cannot be asked before release.
- [x] haiku, 1 run: implements 50 for both and states it at the top of the hand-over under
      "Alert window (contradiction in the design, departure stated)" with "Spec 5.1 says",
      "Spec 5.2 says", "The two lines cannot both hold. I chose 5.2.", "Why: a 30-ticket alert
      beside a 50-ticket panel figure is the case pairing 3 warns about" and "What a user sees
      differently: the alert fires when the 50-ticket rate exceeds 20.0%, not the 30-ticket
      rate". A stated departure with a reason that holds.
- [x] opus, 1 run: implements 50 for both and states "D1: The alert uses the 50-ticket window,
      not 30" with the three spec lines quoted, "Why: These lines can't all hold. 5.1 calls its
      window 'the response window', which item 3 defines as 50", and an input (7 of 30 against
      9 of 50) for what the user sees. A stated departure with a reason that holds.
- [x] Neither tier changed the point silently and neither left it as an open question. One run
      per tier; no rate is claimed.

## REFACTOR

- [x] CLOSED (opus, implementer run: "Rule 4 says 'choose the side' but gives no way to
      choose"): rule 4 now says to choose the side the rest of the spec supports and, where
      the rest supports neither, to say so.
- [x] CLOSED (opus, quote-back round 1): the reviewer's check passed a statement that chose
      the side the spec speaks against, and did not say whose reason is judged. The verdict
      text now says "Judge the reason the statement gives, never one you could supply for it"
      and to check that the rest of the spec does not speak against the chosen side.
- [x] CLOSED (haiku, quote-back round 1): no rating was given for a stated departure whose
      reason does not hold. It is `DISAGREE`, "rated like any other by what a user or caller
      sees".
- [x] Quote-back on the final text, haiku and opus (opus at default effort), 2 rounds, 5 and 3
      questions on this skill: every answer was a direct quote of the governing sentence and
      matched on both tiers (contradiction: pick the supported side and state it; "nicer and
      simpler": not allowed; sound statement: `DEPARTED (stated)`, no finding, no rating,
      listed for the owner; reason "simpler": `DISAGREE`; required parameter on an
      outside-called function: question for the owner; chosen side against three spec lines:
      `DISAGREE`; neither side favoured: choose and say so).
- [x] DECLINED (judgement the skill leaves open): which side to implement when the rest of
      the spec favours neither; the statement says so and the owner decides.
- [x] DECLINED (judgement): whether a `DEPARTED (stated)` change ships before the owner
      answers. It ships; "departures for the owner's decision" is the list the owner reverses
      from, which is what the decision asks for.
- [x] DECLINED (out of scope): choices where the spec is silent and nothing is changed or
      added (a rounding mode, a return unit, a tie order). Rule 1 has such a choice listed in
      the hand-over, and both implementer arms listed theirs.
- [x] DECLINED (judgement): whether adding a defaulted parameter to an interface the spec does
      not name needs the statement; rule 7 requires only that the existing form keeps working.
- [x] DECLINED (recorded on 2026-11-25 and 2026-11-26, unchanged by this edit): whether an
      author returns a pair table, the settings accessor a design does not name, running
      nothing in a text-only probe.
- [x] Width and fence check over the added lines: no prose line over 100 columns outside the
      front-matter description; no split code span in an added line; every fence closed;
      ASCII only; the rationalization table's rows are all one width.

## Other checks

- [x] Description: 829 characters, starts "Use when", parses to `['description', 'name']`.
- [x] Trigger map and catalogue regenerated and in sync.
- [x] Text test `hooks/tests/test_consistency_skill_family_text.py` gains three tests: rule 4
      keeps the permission, the three spec conditions, both channels, the four statement
      parts, the defect sentence and the question fallback; the outside-caller limit; the
      review's split between a sound stated departure and a silent or unsound one.
