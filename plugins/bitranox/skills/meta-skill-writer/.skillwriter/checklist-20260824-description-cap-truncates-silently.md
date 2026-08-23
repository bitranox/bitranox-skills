# skill-writer checklist - meta-skill-writer (over the description cap is truncated, not refused)

Change: the frontmatter section states what happens PAST the 1024-character `description` cap, and
the deployment checklist requires the field to be measured. The rule is also made mechanical: the
commit gate now fails a description over the cap (`harness_checks.DESCRIPTION_CAP`).

## PLAN

- [x] Skill type: reference/hub for skill authoring. Test approach: text check of the artifact, plus
      a diagnosis scenario against the new text.
- [x] Scope: one frontmatter bullet with four sub-points, one deployment checklist line, and the
      gate check with its tests. No frontmatter change to this skill itself.
- [x] Checked against EVERY shipped skill first: the number 1024 appears twice in this skill and once
      in the vendored Anthropic best-practices file, always as a bare limit. Verified with
      `claim_check.py --pattern 'truncat' --control '1024'` over both: ABSENT, control matched 4
      times across 2 files, so the files were read. No other skill mentions the cap at all.

## RED

- [x] A behavioural RED is not available on this machine: `redcheck.py --corpus-cascade` assembled
      827 documents and reported STRONG inherited coverage, naming the fact body that already carries
      the lesson. Route taken, per this skill's own rule: TEXT CHECK of the artifact, recorded above.
- [x] The RED against the FILE failed before this change: an author who read the cap as a validated
      limit had no reason to measure the field, and the skill gave them no symptom to recognise when
      a shipped trigger stopped working.

## GREEN

- [x] Diagnosis scenario (an index skill whose two newest tools are never suggested, nothing logged,
      the file re-read twice and found clean): the agent named the truncated tail as the cause,
      chose a rewrite over a trim, and gave measuring the field as the first command.
- [x] Quote-back, where a new clause goes: "A bloated description is a REWRITE, not an append. An
      appended trigger lands in the dead tail, and inserting one early only pushes a different one
      out." The agent answered "not at the end, and not early either".
- [x] Quote-back, how to confirm rather than assume: "Measure the field, do not eyeball it" and the
      comparison against the injected listing.
- [x] The intended refusal held: asked for the exact number of characters the field can hold, the
      agent declined to give one and quoted the text that refuses to pin it.

## REFACTOR

- [x] Every gap the run reported is closed or declined:
  - CLOSED: "Do not treat 1024 as the cut point" did not say which DIRECTION, and was read as
    "the knife may fall earlier", which would make an author rewrite a safe 900-character field. The
    text now states that the observed cut falls LATER, so nothing under the cap is at risk.
  - CLOSED: no safe target was given beyond "stay under the cap". The text now points at the
    500-character target already stated two bullets below.
  - CLOSED: no procedure for viewing the injected listing. The text now says to ask a running agent
    to quote its own entry and diff it, and says why it cannot be read off disk.
  - CLOSED: nothing checked the length at authoring time. It does now, and the bullet says so.
- [x] GREEN diffed against the pre-change text in BOTH directions: the surrounding CSO rules
      (trigger-first, no workflow summary, the 500-character target) are untouched and still
      reachable, and the new sub-points sit under the cap bullet rather than in front of them.
- [x] The mechanical rule is preferred to the remembered one, per this skill's own guidance that a
      constraint enforceable with validation should be automated rather than documented alone. The
      documentation states the symptom, which validation cannot teach; the gate enforces the number.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] The two figures quoted are evidence, not narrative: a 1060-character description delivered
      whole, and a 2124-character one losing its last 597.
- [x] Body stays a hub: four sub-points on an existing bullet, no new section.

## Deliverables

- [x] Frontmatter bullet and deployment checklist line in `SKILL.md`.
- [x] `DESCRIPTION_CAP` and the over-cap check in `hooks/harness_checks.py`.
- [x] Three tests in `hooks/tests/test_harness_checks.py`: over the cap fires, exactly at the cap
      does NOT fire (the direction that must stay silent), and every shipped skill is within it.
      The last one was RED on `compuse-toolbox (1060)` before that skill's description was rewritten.
