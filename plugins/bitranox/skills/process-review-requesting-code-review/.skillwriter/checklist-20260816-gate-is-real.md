# process-review-requesting-code-review: what makes a verification gate real

Scope: one new section, "A gate is real only when the actor cannot satisfy it", between the
`Before merging` line and `## Example`. No other section changes. A companion change in
`meta-dream-tree/references/dream-core.md` is unrelated in content and stands on its own terms.

## The finding this adds

A review is a verification gate, and the skill already relied on two properties of a real gate
without naming either: the reviewer is a SEPARATE subagent that never saw the session, and
"I already tested it" sits in the Red Flags table. Neither said WHY. Without the principle, a reader
extends the skill in ways that keep the shape and lose the property - most often by having one agent
grade another, or by putting the rigour in a role name.

Measured across five agent orchestrators: four shipped verification that could not refuse. What
separated the fifth was WHERE the gate lived, not effort or code quality.

## RED: behavioural arm unavailable, and why

- [x] `redcheck.py --corpus-cascade` over this tree reports `INHERITED COVERAGE ... STRONG`: the
      lesson is already carried by the always-loaded cascade and the curated store on this machine,
      so a dispatched agent answers the scenario from context handed to it before the prompt. A
      behavioural RED cannot fail honestly here.
- [x] Route taken, of the two the tool offers: a TEXT CHECK of the artifact plus QUOTE-BACK.
      Quote-back is immune to the inheritance - a correct answer must reproduce wording that exists
      only in this section, and inherited context can restate an idea, not a sentence.

## What the tests showed

- [x] Text check per required element. First run found `structurally` ABSENT: the section argued
      the principle without the word separating "cannot" from "was told not to". Fixed; re-run has
      all of `STRUCTURALLY`, `role name in a prompt`, `LLM grading a peer`, `regex over prose`,
      `authenticated identity`, `own permissions`, `exit code`, `five agent orchestrators`.
- [x] Quote-back round 1, on a CI step whose gate is a subagent prompted "You are a rigorous senior
      code reviewer": both answers returned as verbatim quotes, not paraphrase. Q1 returned
      "A gate is real only when that actor is STRUCTURALLY incapable of satisfying it - not merely
      instructed not to."; Q2 returned the table cell `a role name in a prompt ("act as a reviewer")`.
- [x] Round 1 reported a CONTRADICTION the edit itself created: the section says the reviewer is a
      SEPARATE subagent, implying separateness protects, while the table lists "an LLM grading a
      peer, or itself" as unconditionally not gating, with no carve-out. In a skill whose whole
      subject is dispatching an LLM reviewer, that reads as self-cancelling.
- [x] Reconciled by separating the axes - an LLM reviewer FINDS, it does not AUTHORIZE - then
      re-tested. Quote-back round 2 answered YES with the verbatim new paragraph and identified the
      resolution unprompted: "the table classifies what counts as a *gate*, while a separate
      sentence classifies what the reviewer is good for (*finding*)."
- [x] Round 2 gap, closed: a circularity - findings cannot be gated on, because a script checking
      for a finding is "a regex over prose the agent writes". The text now says to gate on the FIX,
      not the FINDING, naming that trap.

## Gaps declined, with reasons

- [x] Who holds "a separate job with its own permissions" (human, CI account, second process) is
      deployment-specific. The property is the content; naming an actor would narrow it wrongly.
- [x] What to do when reviewer and gate disagree is conflict resolution, not what makes a gate real.
      Out of scope for this section.
- [x] The five orchestrators are not named. Naming them dates the skill, and the principle stands on
      its own reasoning - the measurement is corroboration, not the argument.
- [x] "No recipe for verifying *has tests* specifically" - correct, and deliberate. This section
      states the test a gate must pass; choosing a mechanism per stack belongs to whoever builds it.

## Quality

- [x] No narrative or private provenance: the section states the rule and the measurement, not how
      the measurement was come by.
- [x] No machine-specific values added:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over the section returns nothing.
- [x] The table earns its place - three failing shapes against three working ones is a comparison,
      which is what a reader needs at the decision point; prose would bury the pairing.
- [x] Token budget measured and DECLINED as out of scope, not skipped. The file is 873 words
      against the <500 target for a process skill; it was ~590 before this section, so deleting
      this contribution entirely would still leave it over. Bringing the skill under budget means
      rewriting sections this change does not touch and has not tested, which belongs in its own
      reviewed change. What was in scope was done: the section was cut from 27 lines to 21 after
      the first draft, and only grew again to close the two review gaps recorded above.
