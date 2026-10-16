# skill-writer checklist - process-plan-writing-plans (2026-10-16, fold23)

- [x] Change: new section "## Plans Over a Day's Work: Three Altitudes" between "Scope Check" and "File Structure" (freeze inputs with the commit noted; elephants-in-the-room review; HIGH then MID then DETAILED, each checked against the one above; detail only to the next decision checkpoint).
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit the skill had no text for the rule. Verifier gap: "The existing 'Scope Check' (line 24) and 'Self-Review' (lines 160-168) work only at task and spec-coverage level. They would steer the agent toward the single detailed plan the rule warns against." Behavioural RED replaced on purpose because the rule is in the always-loaded memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier): three altitudes -> SKILL.md "When the work spans
      more than a day, do not write one detailed plan", "Freeze the inputs.", "Run an
      elephants-in-the-room review", "Write three plans top-down", "Detail only to the next
      decision checkpoint".
- [x] Gaps closed or declined: Self-Review "add the task" contradicted the deferred-milestone rule;
      closed with an exception in Self-Review ("except for a milestone past the next decision
      checkpoint of a three-altitude plan"). Who judges "more than a day" is left to the planner
      (declined, judgement).
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
