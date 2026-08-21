# skill-writer checklist - process-review-receiving-code-review (right defect, wrong trigger)

Change: a third outcome beside accept and push back - a finding whose stated TRIGGER is unreachable
while the DEFECT it points at is real - plus the step that finds the reachable neighbour of an
unreachable trigger. One line of the Response Pattern, one new section.

## PLAN
- [x] Skill type: discipline/judgement. The change adds a branch to an evaluation the skill framed
      as binary, so the test has to be a scenario, not a text check.
- [x] Trigger is measured on a real review: a reviewer flagged a narrowing cast and reached for a
      trigger orders of magnitude outside anything the hardware produces, while the cast was sound
      only because an independently maintained floor stayed above what a resolution formula needed.
      Declining on the trigger would have kept latent fragility in a safety check; accepting as
      stated would have logged a mechanism that cannot happen.
- [x] Checked it is not already shipped: no hit for "unreachable", "third outcome" or "wrong reason"
      in the SKILL.md before the edit; the Response Pattern's step 5 read "Technical acknowledgment
      or reasoned pushback" and "When To Push Back" listed six accept-or-decline conditions.

## RED
- [x] Scenario dispatched to an inert probe (no filesystem tools) with ONLY the pre-change sections:
      a narrowing cast flagged with a trigger that no configuration produces, while the real
      invariant lives in another file owned by another team, unstated and untested. De-telegraphed
      into a buffer-allocator domain rather than the domain the finding came from.
- [x] RED did NOT cleanly fail, and that is recorded rather than explained away: a capable model
      produced a good answer anyway. It is the known capable-model route-around, and the probe's own
      gaps section is the evidence the gap is real - it reported that the sections "are written as
      if a review comment sorts cleanly into one bucket or the other. This comment doesn't... The
      guidance is silent on this hybrid case - I synthesized a response from its general
      instructions rather than following an explicit branch, since none fit."
- [x] So the coverage evidence for this edit is the probe-reported gap plus the text check against
      the file, not a behavioural flip. Stated here rather than escalating the scenario until
      something failed.

## GREEN
- [x] Same scenario, same model tier, post-change sections: the probe split the finding explicitly -
      declined the stated trigger by name, kept the defect, and proposed the bounds check, a
      boundary test and a comment naming both files.
- [x] Diffed against RED in BOTH directions. GREEN kept everything RED produced. The one RED-only
      item was a scenario-specific unit ambiguity (decimal vs binary megabytes), not a result the
      skill drives, so it is not a lost result.

## REFACTOR
- [x] GREEN's reported gap is IN the shipped text now, and it is the strongest thing the run
      produced: "the guidance never explicitly says to go looking past the stated trigger for a
      live variant of it." Both probes independently re-ran the reviewer's arithmetic with the real
      constants and found a reachable neighbour of the unreachable trigger - so the skill now says
      to do that BEFORE splitting, because skipping it means declining a finding that was live.
- [x] Gap DECLINED with a reason: "involve your human partner if architectural" gives no test for
      where that line sits. Real, but it belongs to the existing pushback section and to
      `process-agents-subagent-driven-development`, not to this one; widening here would put a
      second answer in a second place.

## Design decisions
- [x] The example in the section is stated by SHAPE (a narrowing cast, a floor maintained elsewhere)
      with no repository, PR number or identifiers. The mechanism is what transfers; the citation
      would only be provenance.
- [x] Step 5 of the Response Pattern is amended too, not just the new section. Leaving the pattern
      binary would have kept the shortcut that the section exists to remove - a reader following
      the numbered steps never reaches a section the steps do not mention.
- [x] Named "SPLIT the finding" rather than "partially accept". Partial acceptance still scores one
      verdict on the whole comment; splitting says the two halves resolve independently, which is
      the actual instruction.
- [x] The closing tell ("the trigger is easy to refute and refuting it feels disproportionately
      satisfying") is kept deliberately: the failure mode is motivational, not analytical, and a
      reader who notices that feeling has a hook the technical criteria do not give them.

## Quality
- [x] ASCII only; verified by byte scan. No addresses, hostnames, usernames or private paths.
- [x] Present tense, no session narrative in the shipped section.
- [x] Token budget: 1084 -> 1470 words. Above the 500-word process-skill target; this skill was
      already well past it, and the addition is one branch of its core judgement rather than
      reference material that could be pushed to a file.

## Deliverables
- [x] SKILL.md: Response Pattern step 5, and the "The third outcome: right defect, wrong trigger"
      section including the re-run-with-real-numbers step.
- [x] From the upstream contribution queue; version bumped and CHANGELOG entry added in the same
      change.
