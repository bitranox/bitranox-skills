# skill-writer checklist - meta-dream-tree (2026-10-16, fold contradiction fix)

- [x] Change: `references/dream-passes.md` Durability: "never pushes" now reads "never pushes on
      its own", and names the one push the file describes (the force-push in step 4 of "Bound
      history growth") as running only inside a squash the user approved.
- [x] Change: `references/dream-passes.md` "Bound history growth" step 4: the
      `git push --force-with-lease=<branch>:<old>` runs only on the user's go for this squash, or
      is left for the user to run.
- [x] Ground truth: no shipped script in the plugin runs `git push` (a grep of every non-test `.py`
      under `hooks/` and `skills/` finds push only in guards and gate-verb lists), so the dream's
      own tooling never pushes; the same file already says pushing to a backup remote "stays a
      deliberate act" and that a squash is "propose it first". The two texts now agree with both.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit Durability said "the dream never creates a
      remote and never pushes" while squash step 4 told the dream to force-push a backup remote,
      with no statement that the push needs the user's go. Behavioural RED replaced on purpose
      because the push rules are in the always-loaded memory index of the authoring machine
      (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): no rules to add;
      contradictions: Durability "never pushes" vs squash step-4 force-push -> resolved,
      references/dream-passes.md:175-178 "the dream never creates a remote and never pushes on its
      own ... the one push this file describes (the force-push in step 4 of 'Bound history
      growth') runs only inside a squash the user approved" agrees with dream-passes.md:214-215
      "run only on the user's go for this squash (or left for the user to run)" and with
      dream-passes.md:223 "never auto-create or push"; unlinked md: none in job (dream-passes.md is
      linked from SKILL.md:23); step-4 scan of the dream-passes.md diff: no non-ASCII, no
      hostnames/paths, no private provenance.
- [x] Gaps closed or declined: none.
- [x] Description measured: unchanged (SKILL.md not edited)
- [x] `test_dream_skill_contracts.py` and `test_fence_walker_parity.py` pass after the edit.
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
