# skill-writer checklist - process-agents-subagent-driven-development (2026-10-22, dispatch restriction)

- [x] Change: File Handoffs gains "A restriction you add beyond the brief". A "do not run X" the
      coordinator adds to a dispatch reaches the implementer with more force than the brief, and in
      auto mode the permission classifier enforces it, so it can refuse a step the brief requires.
      Before adding one the coordinator reads the task's full step text in the brief file, never a
      filtered view of the step headers (which drops a step's continuation lines), then routes it:
      no step needs the action and nothing is ambiguous -> drop it; a step needs it -> the step
      wins, and an action still unacceptable for its target or data is a constraint the plan does
      not state; a real ambiguity the plan or an earlier task settles -> a positive pointer under
      item (4) quoting the brief text; anything the plan does not settle -> ask the human before
      dispatching, then put the answer into the plan and regenerate the brief.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`), skill loaded by the editing agent
- [x] Skill type: discipline rule for dispatch composition; test approach: quote-back application
      probe on the pasted text, both tiers, with a control case
- [x] Corpus check: `redcheck.py --corpus-cascade` reported INHERITED (STRONG) by term overlap. The
      top-scoring document's only prohibition line is a different lesson (a brief's prohibition
      does not bind, so grep the fixer's diff); nothing in it tells a coordinator to check an added
      prohibition against the step text. Route kept: a text check of the pre-edit file plus a
      behavioural quote-back arm on the pasted excerpt, declared the text under test.
- [x] Text check (pre-edit `git show HEAD:` of SKILL.md): a case-insensitive grep for
      prohibit|forbid|restrict|do not run|must not|full step text found only the Agent tool's effort
      restriction, unrelated. Pre-edit text: NONE.
- [x] RED (pre-edit File Handoffs excerpt, `bitranox:baseline-probe`, Skill gaps requested), haiku
      and opus: both answered NONE to "quote the line that tells you what to check before adding a
      prohibition the brief does not contain". Both still chose to re-read before sending, because
      the scenario named the filtered view; that choice is not counted, the quote-back is.
      RED gaps: whether an added prohibition is item (4) or a requirement; what to do with a new
      constraint the plan lacks; that item (4) has no anchor to brief text.
- [x] GREEN (post-edit excerpt, de-telegraphed scenario: "glanced at the step titles", db reset),
      haiku and opus: (1) read the full brief, quoting "Before adding one, read the task's FULL
      text in the brief file"; (2) Step 3 needs db reset -> no prohibition, quoting "a step needs
      the action you meant to forbid: the step wins"; (3) control, "clean" ambiguous -> a positive
      pointer quoting the brief, not a ban, quoting "never as a bare prohibition". Every quote
      checked against the pasted excerpt.
- [x] GREEN vs RED diffed both ways: RED's re-read-first behaviour is kept; nothing RED produced is
      missing from GREEN.
- [x] Gaps closed: drop vs ask had no test (now: drop when the worry was the action itself; a
      target or data concern goes to the human); a worry about the TARGET mixed with the action
      (now routed as a constraint the plan does not state); an ambiguity nothing settles (item (4)
      only when the plan or an earlier task settles it, otherwise ask); short context (now "Short
      context is no exception"); "amend the PLAN or ask the human" had no order and amending with
      an unchosen meaning is picking it (now: ask first, then put the answer into the plan); the
      case where no step needs the action had no route (now its own first bullet: drop it); the
      first and last bullets ended differently for the same target concern (now one ending).
- [x] Gaps declined: the plan-contradiction procedure and the stale-brief section are outside the
      pasted excerpt and already in SKILL.md; whether other tasks may proceed while a question is
      pending (pre-existing, owned by plan-contradiction handling); what counts as an earlier task
      "settling" a meaning (judgement the skill leaves open); a narrowed restriction that restates a
      step ("delete only as Step 4 directs") adds nothing the brief does not say; a brief too long
      for the remaining context (reading one task's brief always fits a dispatching session); how a
      subagent asks the human (the coordinator asks; probes return questions to it).
- [x] Re-probes on the final text after each fix round, haiku and opus (opus at effort medium):
      round 1 cases (a) short context, (b) step needs the deletion, (c) staging target, (d) unsettled
      meaning, (e) meaning settled by an earlier task's interface note - all decided correctly with
      verbatim quotes; round 2 (c) (d) and (f) no step needs the action - correct; round 3 on the
      final text (b) (c) (f), haiku and opus: (b) no restriction, quoting "the step wins. Drop the
      restriction when your worry was the action itself"; (c) ask the human before dispatching, then
      into the plan, quoting the last bullet; (f) drop it, quoting "no step needs the action and
      nothing is ambiguous: drop the restriction". No new undecided gap. Both tiers raised a step
      whose action is conditional ("if the build fails, delete the cache dir") and both resolved it
      under "the step wins" from the existing text; declined: the condition is brief text the full
      read already covers.
- [x] Security scan: prose-only diff, no paths, hosts, secrets or PII; example values are generic
      (restore-wu, db reset, a cache dir, staging)
