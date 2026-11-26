---
name: coding-failure-modes
description: Use when failure modes, edge cases or environment variants of a required behaviour have to be found before they fail silently, as its author or its reviewer, in any language - a feature that does nothing on some machines or for some users though it works on the author's, a threshold, a "for N seconds" or a "more than X percent" rule that fires on one sample or never fires, input that arrives empty, late, twice, out of order or half-written, overlapping runs, a crash between two steps, a first run with no state yet, the same name in another case, spelling or Unicode form, a locale with another decimal sign, alphabet, time zone or daylight saving change, another operating system or filesystem, an unset setting, or a hand-over that lists no assumptions about any of these.
---

# Failure modes of a required behaviour (any language)

A required behaviour is written for the case its author pictured. The environment supplies the
others: fewer samples, another order, another spelling, a second process, no state yet. The
defect this skill is about has three parts every time: a behaviour the spec REQUIRES, a way the
environment varies that nobody wrote down, and a failure nobody sees, because the code raises
nothing and the behaviour simply does not happen. It is prevented by walking a fixed list of
axes for each required behaviour and writing a decision per axis, and found in review by
walking the same list from the spec before reading the code.

> Scope: the variants a working environment supplies in ordinary use. A dependency that is down,
> slow or rate-limited belongs to `bitranox:coding-resilience`; input built to do harm to
> `bitranox:coding-input-sanitization`; which boundary values a test feeds in to
> `bitranox:process-test-design`. This skill decides WHICH variants exist and what each one gets.

## The ten axes

Walk all ten for each required behaviour. "Ask" is the question; the example is how the axis
fails without an error.

| #  | Axis                         | Ask                                                                           | Fails silently as                                                                  |
|----|------------------------------|-------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| 1  | Quantity                     | Can there be none, one, two, or more than fits?                               | A share over zero rows; "the average of the last 20" when three exist              |
| 2  | Samples behind a rule        | For a rule over a span or a share: how many samples, how spread, largest gap? | Two samples at the ends of the window pass "every sample in the window is low"     |
| 3  | Order and repetition         | Can events come in another order, twice, or after their successor?            | A refund booked before its payment; a redelivered message counted twice            |
| 4  | Timing and in-progress input | Can the input still be changing, or carry another clock than yours?           | A file read while its upload runs; a reading stamped by a device clock that leads  |
| 5  | Concurrency                  | Can two instances, runs or users act on the same thing at once?               | The next scheduled run starts while the previous one still works on the same items |
| 6  | Interruption and leftovers   | What if it stops between two steps, or is retried after half a success?       | Rows committed, the file not yet moved: the next run imports it again              |
| 7  | First run and long absence   | What if there is no state, directory or history yet, or a week of backlog?    | "Changed since the last sync" with no last sync selects nothing                    |
| 8  | Representation of one thing  | Under which other names or forms does the same thing arrive?                  | `REPORT.CSV` beside a `*.csv` match; a name typed in another case or Unicode form  |
| 9  | Locale and convention        | Which decimal sign, date order, alphabet, sort order, time zone, encoding?    | `12,5` read as text; an A-to-Z index that drops names starting with another script |
| 10 | Platform and configuration   | Which operating system, filesystem, version, permission, unset setting?       | A rename across filesystems; an optional setting absent in production              |

Three of them hide behind the normal case:

- **Axis 2 is not axis 1.** A rule over a span or a share ("below 5 for the last 3 minutes",
  "no login in 30 days", "more than 10% of the rows") has a number of samples behind it.
  Decide the fewest samples that may carry the verdict and, for a span, the widest gap between
  two of them. Checking that the samples reach both ends of the span says nothing about what
  lies between.
- **Axis 8 includes names the environment changes for you.** The same object can be reported
  under another identifier depending on what happened before it (a renamed temporary file, an
  event that carries a different code when another one preceded it, a path with and without a
  trailing separator). List the forms the SOURCE can emit, not the forms the example shows.
- **Axis 9 includes a table that has no entry.** A lookup through the user's own locale,
  alphabet or layout returns nothing where that locale lacks the item, so a behaviour that
  depends on the lookup can never happen there. Ask what the lookup returns in a locale that is
  not yours.

## When you write the change

1. **List the required behaviours.** One line per "must", "when X then Y" and numbered
   requirement the change implements. Helpers get no row of their own.
2. **Walk the ten axes for each behaviour and write the variants down.** A variant is concrete:
   "window holds two readings 170 s apart", not "sparse data". The normal case is not a
   variant and gets no row. A boundary of one quantity ("exactly 10%") is a test input; a
   variant is another KIND of situation. Where you do not know what the environment supplies
   (does the uploader rename when it is finished?), the variant goes in as a question; it does
   not drop out.
3. **Give every variant one of four verdicts.** There is no fifth, and an empty cell is the
   defect this skill exists for. A variant served only in part is two rows.
   - `HANDLED` - the code serves it. Name the line that does (the function, while no file
     exists) and the test: written, or described by its input and expected result for whoever
     writes the tests. Served through a condition the spec lacks, it is still `HANDLED`, marked
     with the departure it rests on (step 7).
   - `REFUSED` - the code cannot serve it and says so where a person or a monitor sees it. Name
     that place (step 5).
   - `ASSUMED` - left out because of a statement about the environment. Write the statement,
     who can confirm it (a role or a task, where you know no person), and what the user sees
     if it is false. When that last answer is "nothing", the row leads the open questions.
   - `NONE` - the axis does not exist for this behaviour. A few words why ("the share is over
     the rows of one file, no clock involved"). State that a caller keeps for you is not
     `NONE`: it is `ASSUMED`, naming the caller.
4. **Trace one concrete input per `HANDLED` row through the code you wrote.** Take the variant
   as literal input and follow it line by line to the result. A sentence in the hand-over such
   as "lower case works too" is a claim until an input has been walked through the comparison
   that decides it. Where you cannot run the code, say that the trace was read, not run.
5. **Turn every silent outcome into a visible one.** A variant that ends in "nothing happens"
   needs a trace somebody will read:
   - **Unmatched is reported.** Items that are neither processed nor rejected are counted and
     named ("2 files in the inbox match no pattern: `REPORT.CSV`, `a.csv.part`").
   - **A precondition that can be checked at start is checked at start.** When a configured
     behaviour cannot work in this environment (the lookup has no entry, the directory is on
     another filesystem, the setting is unset), say so then, not at first use hours later.
     Refuse to start when the required behaviour cannot happen at all; log one warning that
     names the behaviour and the cause when the rest still works.
   - **"No data" is a third answer, not `False`.** A check that returns "not stalled", "not
     expired", "no match" when it could not tell reports a healthy state. Where the return type
     has room, return the third state. Where a fixed signature has none, return the answer
     that claims least, log a warning when the state changes (not on every call; once per run
     in a job that keeps no state between runs), and make it the first open question in the
     hand-over, naming who must surface it. Do not carry the third state out through a new
     exception or a companion function: both change the contract for callers you cannot see.
   - **A fallback taken is said once**, with the value it fell back to.
   - **Refused is not crashed.** A refusal ends the one item or call with a result somebody
     reads, and the other items go on. An exception that stops the whole run on a variant
     ordinary use supplies is a new failure mode: the items behind it are never handled, and
     in an unattended job nobody reads the traceback.

   Each `REFUSED` row gets a test that asserts the visible signal, not only the absence of a
   crash.
6. **Hand the table over.** It goes in the hand-over as written in step 3, with the `ASSUMED`
   rows and the open questions first. Group the `NONE` rows per behaviour on one line.

   ```text
   | behaviour | axis | variant | verdict | where (line, test) or statement |
   ```
7. **Stay inside the spec while you do it.** Serving a variant often needs a condition the spec
   does not carry (a minimum number of samples, a maximum gap, a file age). Derive its value
   from what the source states (a reading every 10 s gives the expected count and gap); a
   value you cannot derive is a guess and is labelled as one. State the condition as a
   departure in the commit message and the hand-over: what the condition is, why you added
   it, and what the user sees differently. `bitranox:coding-consistency`, rule
   5, has the full form, and its reviewer judges the condition on its merit. A fixed signature
   stays as it is: a variant it cannot express becomes a question for the spec's owner.
   Changing the signature itself is a breaking interface change, which rule 7 there admits
   only as a departure with its own ground and the callers it breaks.

## When you review the change

1. **Build your own table from the spec before you open the author's table or the code.** Same
   steps 1 and 2. A table read first becomes the list you check, and its gaps become yours.
2. **Fill your rows from the code.** For each variant, find the line that decides it and write
   what the code does in place of a verdict. "Nothing, and nothing is logged" is a result.
3. **Compare with the author's table.** Where none was handed in, say so in the review and go
   on from your own. Otherwise report:
   - a variant in your table that the author's lacks;
   - `HANDLED` with no line, or a line that does not do it for the concrete input;
   - `ASSUMED` with no statement, or a statement nobody named can confirm;
   - `REFUSED` whose signal nobody reads (a debug log, a return value the caller drops);
   - `NONE` on an axis that exists.
4. **Write one finding per row that ends silently or wrongly:** the behaviour and its spec
   line, the concrete input, what the code does with it, what the user or operator sees (or
   does not see), and the axis number. Rows with one cause share one finding.
5. **Rate by who meets the variant.** High: a required behaviour does not happen, or happens
   wrongly, for a variant ordinary use supplies, and nothing reports it. Medium: the same with
   a visible signal, or a variant that needs an unusual but possible environment. Low: only
   the trace is missing or late. An uncaught exception is a signal only where somebody reads
   it; in an unattended job, rate a crash by the items it leaves unhandled.
6. **Return your table with the findings.** A review that lists findings without it has not
   shown which variants were looked at.

## Rationalizations (these do not fly)

| Excuse                                                        | Reality                                                                                                                                    |
|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| "The spec does not mention it, so it is out of scope"         | The spec requires the behaviour; the environment supplies the variant either way. Out of scope is a verdict you write down: `ASSUMED`.     |
| "Missing data is not a failure, so returning False is safe"   | False alone reads as healthy. Return it only with the warning and the open question, so somebody knows the check could not tell.           |
| "The samples reach both ends of the window, so it is covered" | Two samples do that. Decide the fewest samples and the widest gap.                                                                         |
| "It only matches the documented form, as specified"           | Then the other forms the source emits are left behind without a word. Report the unmatched, or serve them.                                 |
| "I noted it under known gaps"                                 | A gap needs its three parts: the statement about the environment, who confirms it, what the user sees if it is false.                      |
| "The tests will show it"                                      | Tests written from the same picture of the environment hold the same variants. The table is what tells the test author the others exist.   |
| "It works here"                                               | Here is one row: one locale, one filesystem, one process, state already present.                                                           |
| "Walking ten axes for a small change is overkill"             | Most rows are `NONE` and take a line. The row that is not `NONE` is the one that does not show up in the normal case.                      |
| "It cannot tell, so raising is the honest answer"             | Through a fixed signature a new exception is a changed contract, and it stops the caller's loop: least-claiming answer, warning, question. |

## Execution summary

```
WRITING:   list the required behaviours -> walk the ten axes for each, variants written
           concretely -> one verdict per variant: HANDLED (line, test), REFUSED (visible
           signal), ASSUMED (statement, who confirms, what the user sees), NONE (why)
           -> trace one input per HANDLED row -> no silent outcome: unmatched reported,
           preconditions checked at start, "no data" a third answer, fallbacks said once,
           refused is not crashed -> an added condition is a stated departure
REVIEWING: own table from the spec first -> fill it from the code -> compare with the
           author's -> one finding per silent or wrong row, with the concrete input and what
           is seen -> rate by who meets the variant
RETURN:    the table, ASSUMED rows and open questions first; as reviewer, the findings too
```

## See also

- `bitranox:coding-consistency` - two places that must agree; its rule 5 governs a condition
  you add while serving a variant.
- `bitranox:coding-resilience` - a dependency that is absent, slow or flaky.
- `bitranox:coding-input-sanitization` - what to validate and escape at a boundary.
- `bitranox:process-test-design` - the input battery and the tests for the rows of the table.
