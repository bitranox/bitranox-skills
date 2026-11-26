---
name: coding-consistency
description: Use when a change must be checked for consistency in any language, as its reviewer or its author - inconsistent duplicated logic, two code paths computing the same value or decision differently, a ratio whose numerator and denominator are filtered differently, statistics taken over different windows or sample sets, a hard-coded literal standing in for a configured or per-instance value, code that departs from its spec or plan, or adds a condition the spec never asked for, without stating the departure and a reason that holds, a spec that is unclear, incomplete or contradicts itself on a point the code must decide, a stale comment, docstring or notes file claiming what the code does not do, or a public signature changed beyond its contract. Routes Python to coding-python-consistency and Rust to coding-rust-consistency.
---

# Consistency of a change (any language)

A consistency defect is two places that each read correctly on their own and disagree with each
other: two paths, two halves of a figure, the code and its spec, the code and its own comment. It
is found by putting the two places side by side, and prevented by never writing the second place.
This skill holds the pairings to look for, the rules for whoever writes the change, and the pair
table a review of it returns; a language skill adds the constructs of that language that make two
computations of "the same" value differ, and its search patterns.

> Whether each side is correct in isolation is a different review. A wrong formula used
> consistently everywhere is not found here; a right formula used in one of two places is.

## Route by language

| Code under review | Load as well                                                                                              |
|-------------------|-----------------------------------------------------------------------------------------------------------|
| Python            | `bitranox:coding-python-consistency` (quantile, rounding and case rules that differ; duplicated defaults) |
| Rust              | `bitranox:coding-rust-consistency` (`as` casts, `Duration` accessors, what rustc and rustdoc report)      |
| anything else     | nothing: this skill alone                                                                                 |

Where this text says "the language skill" (the candidate search, the interface diff) and no
language skill exists, take each from the project itself: a search for the rounding, case-folding,
division and percentile calls of that language, and the version-control diff of its exported
names.

---

## The seven pairings

Every finding of this lens is one of these. Side A and side B are both in front of you, or one of
them is the spec.

| # | Pairing                            | What has to agree                                                  | How it goes wrong                                                                                                |
|---|------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| 1 | Sibling paths                      | Two routes to one decision or value give the same answer           | The rule is written once per route (web form and import job, live path and replay) and one copy differs          |
| 2 | Halves of one figure               | Numerator and denominator, cost and volume, cover the same items   | One half is filtered (test accounts left out) and the other is the raw count                                     |
| 3 | Figures and rules that go together | Everything shown or decided together rests on the same samples     | The chart averages the last 100 requests, the alert beside it judges the last 10 minutes                         |
| 4 | A literal and what it stands for   | A formula uses the value the system holds                          | `* 4`, `/ 60`, `0.19`, `"EUR"` typed into a formula while the real value is configured or differs per instance   |
| 5 | Code and the spec's fixed points   | Each number, set, order, name and "stays as it is" the spec states | A different window, an extra minimum, a moved default; the spec said one thing and nothing records the change    |
| 6 | Code and its own prose             | Each claim in a comment, docstring, notes or amendment file        | "Used by the exporter to skip unchanged rows" on a value nothing reads; a notes file describing an earlier draft |
| 7 | An interface and its contract      | A public signature, column, field or message other code relies on  | A new required parameter on a function the spec lists as unchanged; every in-tree caller updated, others not     |

A pair has four things to compare, and a pair agrees only when all four do:

- **Set:** which items are in. Spam, deleted, reopened, the component's own output, the other
  tenant.
- **Rule:** the predicate or formula. Substring or whole word, `>=` or `==`, which percentile
  method, which rounding.
- **Window:** how many samples, how old, counted from when.
- **Unit:** seconds or milliseconds, cents or currency units, bytes per item, and how many
  decimals survive.

Two limits on what counts as a pair:

- **The spec may set two things apart on purpose.** When it defines one figure over all items
  and the rule beside it over a window, each side is compared with its own spec point (pairing
  5) and the two are not a pairing-3 defect. Say so in the row, so the next reader does not
  "fix" it. Where the spec defines both and does not say the gap is meant, list it with the
  suspicions as a question for the spec's owner.
- **A named constant is still a literal when the real value differs per item.** `RATE = 0.75`
  used where every team has its own configured rate is pairing 4 with a name on it. A constant
  is the held value only when the spec or the configuration gives one value for everything.

---

## When you write the change

1. **Before you write a second path, find the first one and call it.** A rule needed in two
   modules moves to a place both import; it is never retyped next to the second caller, not even
   "the same three lines". This includes the test-only and the debug path. Where the spec is
   silent on something the second path must still decide (a missing field, a default), it does
   what the first path does, and the choice is listed in your hand-over for the spec's owner.
2. **One definition per population and per window.** Whatever decides which items count is one
   function or one value. Every figure, and every rule judged beside a figure, takes that result
   as input and does not build its own.
3. **Read a value the system holds; do not retype it.** A rate, a size, a format or a default
   that lives in configuration, in a negotiated setting or on the object goes into the formula
   from there. A default exists in exactly one place, and every other place refers to it.
4. **A fixed point of the spec changes only as a stated departure with a reason that holds.** A
   number, a set, an order, a signature and every "stays as it is" is fixed, and without a
   reason the code does what the spec says. You may change one when you judge it sensible,
   above all where the spec is unclear, incomplete or contradicts itself on that point. Then
   state it as a deliberate departure in the commit message AND in your hand-over, in four
   parts: what the spec says (quote the line, or both lines where it contradicts itself), what
   the code does instead, why, and what a user or caller sees differently. The why names the
   gap, the ambiguity or the contradiction in the spec, or what would break with the spec's
   version; "simpler", "I prefer it" and "someone asked for it" name none of these. Where two
   lines of the spec contradict each other, nothing implements both: choose the side the rest
   of the spec supports (a definition it gives elsewhere, a line that relies on the point),
   and the statement quotes both lines and, where the rest supports neither, says so. A fixed
   point changed without that statement, stated only in notes nobody else reads, or with a
   reason that does not hold against the spec text, is a defect. When you cannot give such a
   reason, the code does what the spec says and your doubt goes to the spec's owner as a
   question. Where you hand back files and write no commit, the statement stands under its
   own heading at the top of the hand-over. An interface that code outside the change calls
   is bound by rule 7 as well.
5. **A condition the spec does not carry goes in only as a stated departure.** A minimum
   sample size, a sustain timer, a cooldown, a rounding step or a fallback that nobody
   specified changes when the user sees something, and it usually SUPPRESSES an output the spec
   promised. You may add one when you judge it sensible. Then state it as a deliberate
   departure in the commit message AND in your hand-over, in three parts: what the condition is
   (with its value), why you added it, and what the user sees differently because of it, which
   is the promised output it holds back and when. The statement is what lets the reviewer check
   the condition and the spec's owner reverse it. A condition added without that statement, or
   stated only in notes nobody else reads, is a defect. Where you hand back files and write no
   commit, the statement stands under its own heading at the top of the hand-over. This covers
   a condition you ADD; a fixed point you would change stays under rule 4.
6. **Write prose last, from the code.** For every sentence in a comment, docstring or notes file
   that says what the code does, point at the line that does it. Stored state that is kept "for"
   something has a reader in this change, or it is not stored.
7. **A listed interface is a contract.** A signature, column name or message the spec names, or
   that code outside the change calls, keeps its exact form. Changing one the spec names is a
   rule-4 departure, stated with its reason, and where code outside the change calls it, the
   existing form keeps working (a new parameter has a default, nothing is removed, renamed or
   retyped): the statement reaches the spec's owner, never a caller you cannot see. A change
   that would break such a caller is a question for the interface's owner, whatever the reason.

## When you review the change

Build the pair table first and write findings from it. The table is part of what you return: a
review that lists findings without it has not shown what was compared.

1. **Collect the rows.** One row per pair, from all seven sources; source N feeds pairing N:
   - source 1: every decision or value the change computes in more than one place, including a
     new copy of something that already existed before the change;
   - source 2: every figure with two inputs (a ratio, a rate, a share, an average);
   - source 3: every group of figures and rules that a user sees together or that are compared;
   - source 4: every literal inside a formula, against where the real value lives;
   - source 5: every point of the spec or plan that fixes a number, a set, an order, a name or a
     signature, and every "everywhere", "the same", "whichever is more", "stays as it is";
   - source 6: every claim in a comment, docstring, notes or amendment file about what the code
     does;
   - source 7: every public name whose signature, column or field the diff touches.
2. **Fill each row:**

   ```text
   | # | pairing | side A (file:line) | side B (file:line or spec point) | set | rule | window | unit | verdict |
   ```

   Fill all four comparison cells in every row. A cell holds what each side does ("all stored /
   non-spam", side A first), `=` when both sides do the same and you looked, or `-` when that
   axis does not exist for the pair (a signature has no window). The verdict is one of:
   - `AGREE` - every cell is `=` or `-`.
   - `DISAGREE` - at least one cell differs.
   - `ONE-SIDED` - side B does not exist: a use the prose claims and no code performs, a spec
     point nothing implements, a stored value nothing reads.
   - `ADDED` - the code has a condition, threshold or step with no counterpart in the spec.
     Write `ADDED (stated)` when the commit message and the hand-over state it as a departure
     with all three parts (what, why, what the user sees differently), and `ADDED (silent)`
     when they do not. A change that has no commit carries the statement in its hand-over
     alone. Where you were given neither text, ask for them; without them the row is `ADDED
     (silent)` and the finding says the two texts were not seen.
   - `DEPARTED (stated)` - the code changes a fixed point of the spec (pairing 5 or 7), the
     commit message and the hand-over state it with all four parts (what the spec says, what
     the code does instead, why, what a user or caller sees differently), and the reason
     holds. Check the reason against the spec text yourself: read the lines the statement
     quotes and confirm that the spec is unclear, incomplete or contradictory there, or give
     the input on which the spec's version breaks what the statement says it breaks. Judge
     the reason the statement gives, never one you could supply for it, and where the author
     chose between two contradicting lines, check that the rest of the spec does not speak
     against the chosen side. Whether the owner will want the change is not your check. A
     changed fixed point without the statement, or with a reason that does not hold, is
     `DISAGREE`, rated like any other by what a user or caller sees, and its finding says
     which of the two it is. A departure that breaks a caller outside the change is `DISAGREE`
     whatever its reason. A change that has no commit carries the statement in its hand-over
     alone.
3. **Write one finding per row that is not `AGREE`, `ADDED (stated)` or `DEPARTED (stated)`:**
   - both locations;
   - a concrete input on which the two sides give different results, with the two results
     (`subject "Outages in hall 2": urgent by form, not urgent by import`). A difference you
     cannot give an input for is a suspicion, and goes in a separate list;
   - which side the spec supports, quoting its line, or "the spec is silent", or "the spec
     reads both ways". Two sides that disagree are a finding in all three cases. A single side
     on a point the spec leaves open is not a finding of this lens, with one exception: an
     `ADDED (silent)` row, because it changes an output the spec did describe and says so
     nowhere;
   - what the user, operator or caller sees because of it. For `ADDED (silent)`: what output
     it holds back, and where the addition is stated (commit message, hand-over, the author's
     own notes, nowhere).

   An `ADDED (silent)` row is a defect. An `ADDED (stated)` row is not: list it under
   "departures for the owner's decision" with the author's statement and your check of it
   against the code. A `DEPARTED (stated)` row is no defect either: list it there too, with the
   author's statement, the spec lines it quotes and your check of the reason against them. A
   statement that names another value or another effect than the code has is a pairing-6
   `DISAGREE` row of its own.

   Prose claims that restate one code row (a notes line and a docstring saying the same false
   thing) share that row's finding instead of repeating it.
4. **Rate by what is seen, and take the higher level when two fit:**
   - high: a path the spec requires behaves differently from its sibling or from the spec in
     ordinary use, or a caller outside the change breaks. A spec that names outside callers of
     a changed interface is such a caller;
   - medium: a value that is displayed, stored or sent, a message or an alert is wrong under a
     condition that can occur;
   - low: nothing a user sees, stores or configures changes (prose only, an interface drift
     with every caller updated). Where no outside caller is known, the finding says that
     callers outside the tree were not checked.

   An `ADDED (silent)` row is rated by what it holds back, on the same scale. An
   `ADDED (stated)` row carries no rating; its entry says what it holds back. A
   `DEPARTED (stated)` row carries no rating either; its entry says what a user or caller sees
   differently.
5. **Then read the change once more for rows you did not collect.** The sources in step 1 are
   where pairs usually are, not a complete list.

The language skill gives a search that lists candidate lines for sources 1 to 4 and the diff that
lists source 7.

---

## Rationalizations (these do not fly)

| Excuse                                                                 | Reality                                                                                                                                                                            |
|------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| "The spec is silent on a minimum, so adding one is within the spec"    | The spec says when the output appears, and the condition holds it back. Add it if it is sensible, as a departure you state, not as something the spec allowed.                     |
| "I flagged it in my notes, so it is a stated departure"                | Notes nobody else reads reach neither the reviewer nor the owner. The statement goes in the commit message and in the hand-over.                                                   |
| "Set the constant to 1 to restore the literal rule"                    | A switch does not replace the statement: the shipped default still departs. Say what it is, why, and which output the user no longer sees.                                         |
| "The spec is plainly wrong here, so I quietly did the right thing"     | Do it, and state it: the spec line, what the code does instead, why, what is seen differently. Unstated, the reviewer reads a defect and the owner never learns the spec is wrong. |
| "I stated the departure, so the change is covered"                     | Only with a reason that holds against the spec text: a gap, an ambiguity, a contradiction, or something the spec's version breaks. A preference stated is still a defect.          |
| "It is the same three lines, copying is simpler than a shared home"    | They are the same today. The second copy is the place the next edit misses, and no test compares the two.                                                                          |
| "Both versions satisfy the sentence in the spec"                       | Then the spec has two readings and the change picked both. Two paths must give one answer; which reading is right is a question, and the pair is a finding either way.             |
| "Every caller in the tree is updated, so the signature change is safe" | The callers you cannot see are the reason the spec listed the signature. Report it; the owner decides.                                                                             |
| "The comment is only slightly ahead of the code"                       | A comment that names a use the code does not have sends the next reader to defend dead state. Point at the line or delete the sentence.                                            |

## Execution Summary

```
WRITING:   find the first path and call it -> one population, one window -> read held values
           -> spec's fixed points as written, a changed one only as a stated departure whose
           reason holds (spec line, what the code does instead, why, what is seen differently)
           -> an unspecified condition only as a stated departure (what, why, what the user
           sees differently) -> both statements in the commit message and the hand-over
           -> prose last, each claim pointed at a line -> an interface outside callers use
           keeps working
REVIEWING: collect rows from the seven sources -> fill set / rule / window / unit per row
           -> verdict per row, ADDED as (stated) or (silent), a changed fixed point as
           DEPARTED (stated) only when its reason holds against the spec text -> one finding
           per row that is not AGREE, ADDED (stated) or DEPARTED (stated), with a concrete
           input, the spec line and what is seen -> second read for uncollected rows
RETURN:    the pair table, the findings, the departures for the owner's decision, the
           suspicions without an input
```
