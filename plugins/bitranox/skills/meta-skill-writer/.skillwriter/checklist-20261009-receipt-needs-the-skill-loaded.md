# skill-writer checklist - meta-skill-writer (the guard also needs the skill loaded by the editing agent)

Change: Step 0 now states the skill-edit guard's two conditions - a fresh session receipt AND the
skill loaded by the agent making the edit, read from that agent's own transcript - and what follows
for a subagent: the parent's receipt covers it, it must invoke `bitranox:meta-skill-writer` through
the Skill tool before its first edit, it needs no `start` of its own, and it must not run `end`.
This syncs the skill with `hooks/skill-edit-guard.py`, which now enforces the second condition.

## PLAN

- [x] Skill type: technique (a procedure step a dispatching agent must follow).
- [x] Scenario drafted before editing: the main agent holds a fresh receipt and dispatches a
      subagent to apply a SKILL.md edit; what must the brief say for the edit to be allowed. A
      control question: the main agent's own later edit, which must need nothing extra.
- [x] Scope: one paragraph of an existing hub skill; no front-matter change, no supporting file.

## RED

- [x] Inherited-context check: `redcheck --corpus-cascade` reported shared vocabulary only
      (dispatch, instruction, marketplace, pretooluse). A grep of the same cascade (1,848 files)
      for the lesson's own terms - a subagent riding the parent's receipt, a skill loaded by the
      editing agent - matched none, while a control term (`receipt`) matched 12, so the grep
      reads the corpus. The behavioural RED stands.
- [x] RED, haiku, pre-change Step 0: no instruction to load the skill; it branched on "if the
      subagent shares the parent's session ID, the parent's live receipt covers its Edit". Gap
      verbatim: "The excerpt does not say whether a subagent (Agent tool) runs under the parent's
      session ID or its own. This is the deciding fact, and the text is silent on it."
- [x] RED, sonnet, pre-change Step 0: "I can't write an instruction that makes the subagent's Edit
      allowed"; governing quote NONE.

## GREEN

- [x] GREEN, sonnet: brief says to invoke `bitranox:meta-skill-writer` through the Skill tool
      before the first edit and not to run `start`; quoted "A subagent that edits a SKILL.md must
      therefore invoke `bitranox:meta-skill-writer` through the Skill tool before its first edit".
      Control: the main agent needs nothing extra, quoting the two-condition sentence.
- [x] GREEN, haiku: the same brief and the same control answer, both with verbatim quotes.
- [x] Every dispatch asked for a "Skill gaps" section; the lists are worked below.
- [x] GREEN diffed against RED in both directions: RED's correct points (do not counterfeit a
      receipt by running `start` in the subagent; the review artifact is a commit-gate matter, not
      the edit guard's) are still present in both GREEN answers; nothing RED produced is lost.

## REFACTOR

- [x] Gap (both GREEN arms) "whether the subagent must run `start`" and (sonnet) "whether the
      subagent can safely run `end`" - CLOSED: "It needs no `start` of its own and must not run
      `end`, which removes the receipt for every agent in the session." Quote-back, haiku: both
      answers quoted that sentence.
- [x] Gap (sonnet) "the main agent's load after a compaction or /clear" - DECLINED: a compaction
      keeps the transcript file, so the load record stays; /clear starts a new session, which
      needs a new receipt and a new load anyway.
- [x] Gap (haiku) "load of `meta-skill-writer` or of the skill being edited" - DECLINED: the
      sentence names `bitranox:meta-skill-writer`.
- [x] Gap (quote-back) "a receipt that has expired" - DECLINED: governed by the existing 8-hour
      sentence under "Last step".

## Quality

- [x] No session narrative or private provenance in the change or this artifact.
- [x] No address, hostname or private path added.
- [x] Front matter untouched.
