# skill-writer checklist - meta-skill-writer (2026-08-12, inherited context voids a behavioural RED)

Change: the "Watch for baseline contamination" section in testing-skills-with-subagents.md gains
the INHERITED-context form of route 2 - a dispatched subagent inherits the dispatching session's
CLAUDE.md cascade and always-loaded memory index, so an inert probe type bounds TOOLS but not
CONTEXT. It states that this is the ordinary case rather than an exotic one, that the cascade and
store must be checked BEFORE a RED is trusted, the two honest routes when the lesson is already
inherited (coverage check against the skill file, or a de-telegraphed arm in an untaught domain),
the requirement to record which route was taken, and that a RED which does not flip is reportable
rather than a reason to escalate. SKILL.md gains the same rule in short form in its RED phase plus
a RED-phase checklist item. Ships with plugin 5.196.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Application scenario.
- [x] Not a new section. Route 2 already covered injected context from a recall hook or RAG layer,
      and its isolation ladder assumes a retrieval setting you can wall off. The inherited cascade
      has no such switch, and the existing text's probe-type framing implied an inert agent type
      was a clean room. An author following it got a false all-clear.
- [x] MECHANISM VERIFIED BEFORE WRITING, not taken on report. One `bitranox:baseline-probe`
      (sonnet, no tools) was asked two questions whose answers exist only in this machine's
      always-loaded index. It answered both, reproduced the worked example a stored rule carries,
      and attributed both answers to its startup context rather than to general knowledge. Tool
      calls: 0. The claim that the probe type bounds tools and not context is therefore measured,
      not assumed.
- [x] RECURSION HANDLED, ROUTE 1 TAKEN AND DECLARED. The lesson under test is itself already in
      this machine's always-loaded index, so by the rule being shipped a behavioural RED here
      cannot fail honestly and was NOT run as evidence. The COVERAGE check is the evidence instead:
      `claim_check.py` over SKILL.md and testing-skills-with-subagents.md, each negative gated on a
      control that matched 37 times across both files. ABSENT for all of: the probe type named at
      all; any tools-versus-context distinction; the cascade, memory store, pointer index or
      always-loaded text as the injector; de-telegraphing into an untaught domain; a non-flipping
      RED being reportable or the escalation ban. One PRESENT hit was unrelated (a sentence about
      shell return codes), read and discarded rather than counted.
- [x] A RED that could not fail honestly was recorded as such, not escalated into a harder scenario
      until something failed - the rule this change ships, applied to this change.
- [x] Behavioural check that inherited context CANNOT forge: a quote-back arm on the new passage.
      The wording is novel, so an accurate verbatim quote of it can only come from the prompt.
      Five contested questions, five direct quotes, zero NONE - what the probe type bounds and does
      not bound, the status of a RED run over an inherited lesson and whether re-running fixes it,
      both routes plus the artifact requirement, the non-flipping outcome and the escalation ban,
      and why the file check is immune and what gates it.
- [x] Gaps list required and worked. Six reported, three CLOSED in the text:
      - "control pattern that MUST match" did not say how to pick one, so route 1 now reads "a
        control pattern you know appears in those files".
      - the text was silent on a coverage check that comes back PRESENT; it now says a PRESENT
        verdict ends the job because the guidance already ships.
      - route 2 gave no way to judge a domain the cascade does not teach; it now says to choose
        that domain with the same check, run against the cascade and store instead of the skill.
- [x] Three gaps DECLINED with reasons: the probe could not verify the checker it was pointed at
      exists (a tool-less probe cannot verify anything, which is the point of the type); the exact
      boundary of "always-loaded" varies per reader's setup and a shipped skill cannot enumerate
      another machine's configuration; a RED that DOES flip needs no new rule, since inheritance
      threatens a PASS and a flip is the informative result the phase is for.
- [x] Written for readers who do not run this plugin: the cascade, memory index and probe type are
      described by what they are, with the toolbox checker named as the one plugin-local pointer.
- [x] Token budget: the treatment lands in the reference file that owns baseline mechanics;
      SKILL.md gains a short rule in the RED phase and one checklist line.
- [x] Frontmatter description unchanged, so `docs/skills.md` needs no regeneration.
- [x] No session narrative or private provenance in the skill text - no memory-fact slug, no
      machine paths. The class is named (a lesson already in the machine's memory store or CLAUDE.md
      cascade), never this machine's specifics. Evidence detail lives in this artifact only.
- [x] No addresses, MACs, hostnames or machine paths added.
