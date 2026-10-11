# skill-writer checklist - meta-skill-writer (when a coordinator runs start and end)

Change: Step 0 states that a coordinator dispatching SKILL.md-editing subagents runs `start` itself
before the first dispatch and runs `end` only after the last of them has reported or been stopped;
a subagent that edits no SKILL.md needs neither the receipt nor the skill load. "Last step" defines
"finished" for a coordinator the same way and says a second `start` renews the 8-hour lifetime
(`skill_receipt.start` rewrites the receipt's timestamp). The "Otherwise, apply the edit" sentence
is reworded to name the case it covers.

## PLAN

- [x] Skill type: technique (a procedure step a dispatching agent must follow).
- [x] Scenarios drafted before editing: (A) the main agent's own change is committed and four
      SKILL.md edits are about to go to background subagents - when does `end` run; (B) a
      coordinator that makes no edit and has not run `start` dispatches nine fixes, three of them
      SKILL.md edits, briefed "do not run start or end".
- [x] Scope: two paragraphs of an existing hub skill; no front-matter change, no supporting file.

## RED

- [x] Inherited-context check: `redcheck --corpus-cascade` flagged inherited coverage. Most shared
      terms were function words; one memory fact body does teach the ordering rule. Route taken: the
      RED arms ran as `bitranox:baseline-probe` (no Read, so no fact body is reachable) and every
      question demanded a direct quote of the governing sentence or NONE, which makes the RED a text
      check of the artifact.
- [x] RED, haiku, scenario A, pre-change text: right action, reached by inference; no quoted
      sentence states it. Gap verbatim: "'The procedure is finished' is ambiguous. Read as 'my own
      edit is committed', `end` could run now, which would break the four subagents."
- [x] RED, sonnet, scenario A, pre-change text: right action by inference; gap: "Last step ...
      assumes one agent making one change. It is silent on whether delegated edits by subagents
      count as part of this procedure."
- [x] RED, haiku, scenario B, pre-change text: right action, quoting only the two-condition
      sentence; gap: "'When the procedure is finished' is undefined for a multi-subagent batch."

## GREEN

- [x] GREEN, haiku and sonnet, scenarios A and B: both arms keep the receipt armed through the
      dispatch (A) and run `start` before dispatching (B), each quoting "So a coordinator that
      dispatches subagents to edit SKILL.md files runs `start` itself BEFORE the first dispatch, and
      runs `end` only after the last of them has reported".
- [x] Every dispatch asked for a "Skill gaps" section; the lists are worked below.
- [x] GREEN diffed against RED in both directions. LOST: RED-B said only the three SKILL.md editors
      need the receipt; both GREEN arms read "every dispatched subagent" in the first draft of Last
      step as all nine. Reproduced across both arms, caused by this edit's own wording - fixed below.

## REFACTOR

- [x] Lost result "which subagents gate `end`" - CLOSED: Last step now reads "every subagent it
      dispatched to edit a SKILL.md", and Step 0 adds "A subagent that edits no SKILL.md needs
      neither the receipt nor the skill load." Quote-back, haiku: with three editors done and four
      Python agents running, "Yes", quoting both sentences.
- [x] Gap (GREEN haiku, sonnet; RED-B) "a subagent that never reports" - CLOSED: "has reported or
      been stopped". Quote-back, haiku: a TaskStop-ed editor counts, quoting that phrase.
- [x] Gap (GREEN haiku, sonnet; RED sonnet) "whether a second `start` refreshes the window" -
      CLOSED: "8 hours after the latest `start`; running `start` again renews it". Quote-back,
      haiku: a 9-hour batch renews with `start`, quoting that sentence.
- [x] Gap (RED and GREEN alike) "'Otherwise, apply the edit in the agent that ran this procedure'
      conflicts with delegating" - predates this edit, CLOSED in the same change: "A SKILL.md edit
      that no skill-loading subagent will make is applied in the agent that ran this procedure."
      Quote-back, haiku: answered from that sentence.
- [x] Gap "a stopped subagent's partial edits" - DECLINED: reviewing or reverting delegated work is
      `bitranox:process-agents-subagent-driven-development`'s subject, not the receipt's.
- [x] Gap "who writes the review artifact for subagent edits" - DECLINED: the artifact rule is the
      repo's, and the paragraph already points at its CONTRIBUTING.
- [x] Gap "`<plugin>` is not a concrete path" - DECLINED: the placeholder is used throughout the
      skill for the installed plugin root, and Step 0 is not where it is defined.
- [x] Gap "no renewal schedule" - DECLINED: the expiry sentence gives the lifetime; when to renew
      inside it is the reader's call.

## Quality

- [x] No session narrative or private provenance in the change or this artifact.
- [x] No address, hostname or private path added.
- [x] Front matter untouched.
