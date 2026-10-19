# skill-writer checklist - meta-self-improve (2026-10-19)

Change: step 2 first asks which skill was in use when each lesson happened, and routes a lesson
that arose inside a loaded skill's domain (or that a never-loaded shipped skill covers) to a queued
fix for that skill instead of a memory fact. The miss-audit paragraph no longer calls skill gaps
"not this loop's job". The Stop gate names the session's invoked skills (`SKILLS IN USE`).

- [x] Skill type: process/technique - tested with an application scenario of five candidates
      (release step, user directive, SSH step, never-loaded Proxmox skill, unrelated git quirk).
- [x] RED (pre-change text, installed copy identical to the source): haiku wrote A (release step)
      and C (SSH step) as memory facts, routing to the skill only "if the skill already covers it";
      opus queued A and C but wrote a fact beside each. Both reported the contradiction between the
      step-2 "PROPOSE" row and "Skill-coverage gaps are NOT this loop's job"; both found no line for
      a skill that covers the domain but never loaded (D quoted NONE).
- [x] redcheck route: the cascade carries `feedback-flag-a-skill-when-a-real-bug-slips-past-it`, a
      related lesson; RED failed anyway, so the behavioural arm stands.
- [x] GREEN (new text pasted over the installed sections): haiku and opus both queued A, C and D
      against devops-bmk, compuse-ssh and infra-proxmox with no memory fact, kept B as a fact, and
      quoted the governing line for each.
- [x] Lost-result diff, RED against GREEN: RED opus noted that A's cwd half overlaps an existing
      wrong-directory fact; GREEN arms noted the same overlap. Nothing a RED arm produced is missing.
- [x] Skill gaps from GREEN, closed: cases were unordered and overlapping (now numbered, first fit
      wins); no case for "no skill in use" (case 3); the fact rule was ambiguous for a trigger miss
      (now "binds work outside that skill's description", with a release example and a shell-quoting
      example); "when the skill lacks it" contradicted "the route does not change" (removed: the
      entry always carries the lesson); a two-lesson candidate had no rule (split first).
- [x] Skill gaps, declined: the `"<cwd>"` and `--proj` choice when the cwd is a temporary worktree
      (a separate defect, filed in OPEN-WORK.md); whether to pin a user directive and `--type user`
      versus `feedback` (step 4 and the backend reference own them); the re-test's missing table,
      skill list and nudge format (absent from that probe by construction).
- [x] Re-test of the touched questions by quote-back, haiku: 6 of 6 answered with a direct quote
      of the governing sentence (trigger miss, unrelated-but-covered git quirk, no skill, split
      candidate, mentioned-but-missed, case priority).
- [x] Gate code: three tests written first and RED on the old gate; removing the hint from the
      reason turns the two skill tests RED again; 133 tests in the gate and memory-system modules
      pass.
- [x] Description unchanged, so skill_triggers.json and the docs catalogue need no regeneration.
- [x] Body edit only; no @ links; table row re-padded to the existing column width.
- [x] Security scan: prose and a hook reading the session's own transcript; no secrets, hosts,
      private paths or PII added.
