# skill-writer checklist - meta-claude-hooks (price a guard before escalating it to a block)

Change: one new section, "Before you escalate a nudge to a block, price it" - measure a guard's
firing rate and PRECISION by replaying the real transcript corpus, with a control arm, before
turning a nudge into a deny.

## PLAN

- [x] Skill type: reference/hub for hook authoring. Test approach: text check of the artifact.
- [x] Trigger is measured, not hypothetical. The gated-prep guard in this plugin has now had the
      same escalation proposed twice on recurrence count alone. Both times the measurement said no:
      a blanket deny scored ~4% precision, and the target-aware variant proposed the second time
      scored 4.04% against 4.14% for the whole hook, with the arm it would have DOWNGRADED scoring
      4.60%. The reasoning that produced both proposals is generic, so the counter belongs in the
      hook-authoring skill rather than only in that one hook's docstring.
- [x] Checked against EVERY shipped skill before writing: no skill documents `guard_replay.py` as
      part of hook authoring. `compuse-toolbox` lists the tool in its index (it owns the script),
      and this skill owns the judgement about when to reach for it, so the section cites the home
      rather than duplicating the tool's documentation.
- [x] Scope: one section plus its invocation example. No frontmatter change - the description
      already triggers on writing and reviewing hooks.

## RED

- [x] Behavioural RED is NOT available on this machine: the lesson was recorded in this session and
      the corpus now contains it. Route taken, per this skill's own rule: TEXT CHECK of the
      artifact.
- [x] The RED against the FILE failed before this change, and failed in the direction that costs
      real work: the skill's pre-write questions and its "five that bite hardest" cover which event
      fires, whether it can block, and how it answers - but nothing told an author how to decide
      WHETHER a block is an improvement. An author following the skill completely still had no
      reason to measure, which is exactly how both escalation proposals were written.

## GREEN

- [x] Text check: the section states what number decides it (precision, not recurrence count), the
      command that produces it with the script's home path, and the three conditions that make the
      number trustworthy.
- [x] Quote-back for the control-arm requirement: "Replay the guard UNCHANGED and require it to
      reproduce whatever figures are already recorded for it. If it does not, the harness is wired
      wrong and no number from any variant means anything."
- [x] Quote-back for why unit tests are not enough: "Unit tests prove a guard fires on the shapes
      you listed. Only a replay tells you whether it is QUIET on everything else."

## REFACTOR

- [x] States the failure mode of the WRONG choice, not only the procedure: a block that is not
      quiet gets routed around, leaving the author worse off than the nudge they started with.
      Without that, "measure first" reads as process rather than as self-interest.
- [x] Names the unclassifiable-shape trap explicitly (an interpreter write exposes no filename), so
      a future target-aware proposal has to account for it before its numbers mean anything. This is
      the specific hole the second proposal fell into.
- [x] Closes with "record the measurement next to the guard", which is what stops the third
      proposal re-running the argument.
- [x] Cross-skill script reference states the owning skill's home (`skills/compuse-toolbox/scripts/`)
      at point of use, not a bare filename.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths (`~/.claude/projects` is the
      tool's own documented default, not a path from this machine).
- [x] Body remains a lean hub section; detail stays in the tool's `--help` and the guard's docstring.

## Deliverables

- [x] One section in `SKILL.md`. No script, so no `tests/` change.
