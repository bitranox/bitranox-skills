# skill-writer checklist - compuse-toolbox (description rewritten to fit the cap)

Change: the frontmatter `description` goes from 2124 characters to 999, covering the same 20 tools.
No body, script or test changes.

## PLAN
- [x] Skill type: reference. This is a CSO change - the description is the field the router reads,
      and nothing else in the skill is touched.
- [x] Trigger is measured, not hypothetical: at 2124 characters the field is truncated mid-word in
      the injected available-skills listing. 597 characters never reached the router, carrying the
      only triggers for two tools plus the closing instruction. Measured across the shipped set: 79
      of 80 skills were already under the cap, median 394.
- [x] Scope: one field, plus the two derived artifacts a description change invalidates.

## RED
- [x] The failing check is a TEXT measurement, not a scenario: `len()` of the extracted field, 2124
      against a documented cap of 1024. Re-run over all 80 skills to confirm it was one skill and
      not a systemic condition.
- [x] Two tests failed on the change and were the right ones to fail:
      `test_shipped_catalog_in_sync_with_skills` and `test_shipped_trigger_map_in_sync_with_descriptions`.
      A description edit invalidates `skill_triggers.json` and `docs/skills.md`; both regenerated.

## GREEN
- [x] 999 characters, 25 to spare, all 20 tools still named.
- [x] Every distinctive retrieval keyword retained, asserted mechanically rather than by eye:
      pgrep, gitignored, UTF-16, BOM, ls sort tail, RED baseline, worktree, CLAUDE.md, memory level,
      guard, JSONL, ssh, conflict, CI log, transfer, source files, computer-use, Claude Code
      transcript.
- [x] 3000 passed, 7 skipped after regenerating the derived artifacts. README skill count unchanged
      at 80, correctly - a script was added, not a skill.

## REFACTOR
- [x] One clause rewritten on a CSO principle rather than on a probe result. `killing a process
      without pgrep/pkill self-match` states the hazard as a PRECONDITION, so it can only match a
      user who has already noticed the hazard - which is not the user who needs the tool. It now
      reads `finding or killing a process with pgrep -f or pkill -f`, matching the words a user
      actually types, and the hazard stays in the body where the explanation belongs.
- [x] Headroom recorded rather than consumed: 25 characters. The next tool added needs a
      compression pass on this field, not an appended clause.

## Declined, with the reason
- [x] LIVE ROUTING IS UNVERIFIED, and it is recorded as unverified rather than dressed up. Four
      probes were asked to judge candidate wording from the prompt alone; every one answered from
      this machine's real context instead. The tell was explicit - one quoted `safely finding or
      killing a process without self-matching pgrep/pkill`, which is the INSTALLED description and
      appears nowhere in the prompt it was given, and another said it was checking "the actual
      available-skills list for this turn". A skill's own wording cannot be A/B-tested on a machine
      where that skill is installed, and an inert agent type does not help because it bounds tools,
      not context. The evidence for this change is therefore the text check above, which inherited
      context cannot affect. A live routing answer would need a machine without the plugin.
- [x] One probe case was mis-chosen and is not evidence either way: it asked whether a deleted
      worktree's disk space should route here, but `wtclean` ships in `git-worktrees`, whose own
      description names that symptom. Routing elsewhere was correct behaviour, not a miss.
