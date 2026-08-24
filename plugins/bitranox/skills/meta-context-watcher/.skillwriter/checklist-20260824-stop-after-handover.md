# skill-writer checklist - meta-context-watcher (the handover is the last thing the session does)

Change: Procedure step 5 becomes a hard STOP - no new task, no resuming the part-done one, not even
the next action just written into the file - and "tell the user to type `/clear`, then wait" splits
out as step 6.

## PLAN

- [x] Skill type: discipline (a rule that has to hold under "it is only seconds of work" pressure).
      Test approach: pressure scenario, both arms, plus a weak-tier re-run when the baseline passes.
- [x] Scenario drafted before editing: handover written, its own "next action" line is a
      one-character rename plus a 3-second test, nothing else pending. Options offered as A apply it
      now / B hand back / C ask first, with the weak-tier arm swapping C for "apply it and refresh
      the next-action line" and adding the stated preference against leaving a tree half-finished.
- [x] Scope: two steps in one existing section. No frontmatter change, no supporting files.

## RED

- [x] Inherited-coverage checked with `redcheck.py --corpus-cascade` over the session's real
      ancestor chain: 821 documents assembled, clean. Not a sealed fixture (the check compares
      distinctive terms and cannot see a paraphrase), but the two leaks it does check are ruled out.
- [x] Baseline run on the pre-change text at two tiers. BOTH chose B, so the behavioural RED does
      not flip - recorded as the outcome rather than escalated until something failed.
- [x] Both baselines independently named the SAME missing line, which is the finding the arm exists
      to produce. Verbatim: "The skill never explicitly addresses the case where the 'next action'
      is trivial and could be finished in seconds before handover. I inferred B from the procedure's
      step ordering (nothing after step 5) ... not from an explicit line telling me not to do
      trivial work." And at the weak tier: "The skill does not explicitly forbid continuing work
      after the handover is written ... leaving the boundary implicit. A reader working against
      time might argue 'it is seconds, the next session can wait' without a line explicitly saying
      'do not.'"
- [x] The weak-tier baseline reached the right answer through the WRONG clause, quoting "Never amend
      a stale handover to update it" - which governs a later session finding this file stale, not
      the writer who just produced it. The stronger baseline flagged that same clause as
      inapplicable for exactly that reason. An answer defended from a rule that does not cover the
      case is the shape a missing rule leaves behind.
- [x] One baseline surfaced an option the prompt had not offered: apply the edit AND rewrite the
      next-action line to match, reported as a case "the skill gives no guidance on either way".

## GREEN

- [x] Post-change text run against the same scenario. Chose B and quoted the new step 5 verbatim as
      what decided it, including the clause aimed at the surfaced fourth option: "not even the next
      action you have just written into the file". Quote-back satisfied - the answer is a direct
      quote of the governing text, not an inference from step ordering.
- [x] Every dispatch, both arms, required a "Skill gaps" section. GREEN reported none for this
      decision; the arms that reported gaps are recorded above rather than summarised away.
- [x] Diffed against the baseline in both directions. Nothing the baseline produced is missing from
      GREEN: same choice, same reasoning about falsifying the file, plus the quote the baseline said
      it could not find. The gap lists shrink because their contents are now in the text.

## REFACTOR

- [x] Gap "no explicit line forbidding trivial work after the handover" - CLOSED. Step 5 names the
      three shapes it forbids (new task, resuming the part-done one, "just finish" the small thing)
      and gives the reason, so the rule survives being read under time pressure.
- [x] Gap "silent on applying the edit and refreshing the next-action line" - CLOSED by the same
      step, which forbids the next action written into the file specifically.
- [x] Gap "does step 5 also cover asking the user first?" - DECLINED. GREEN read it correctly as
      answered by removal ("it doesn't say 'ask first,' it says stop and tell the user to
      `/clear`"), and step 6's "then wait" already ends the turn. An explicit anti-ask clause would
      add a third negation to a step whose force comes from being short.
- [x] Gap "does a prior 'yes, do the handover' authorise further work?" - CLOSED for the case that
      matters by the final sentence: a new request gets the handover, then the stop, then a re-ask
      after the clear.
- [x] The `/clear` instruction moved to its own step rather than staying inside the STOP paragraph,
      so the two are separately quotable and neither hides the other.

## Quality

- [x] `wc -w` 980, a hub-shaped skill whose body is already reference material; the change adds six
      lines to an existing section and no new section.
- [x] ASCII only across the whole file, verified after editing. No em-dashes, no curly quotes.
- [x] No address, MAC, hostname or machine path added - verified over the file, zero hits.
- [x] Present tense, no session narrative, no record of how the step read before this change.
- [x] Frontmatter untouched: the description still states triggers only and summarises no workflow,
      which is what keeps the body from being skipped.

## Deliverables

- [x] `SKILL.md` Procedure steps 5 and 6, applied. No script, so no `tests/` change for this skill.
- [x] Version bumped in `plugin.json`; the skill edit and the hook fix committed beside it ship
      under the same number.
