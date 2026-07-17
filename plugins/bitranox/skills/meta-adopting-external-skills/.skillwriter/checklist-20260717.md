# skill-writer checklist - meta-adopting-external-skills (2026-07-17, step 4 matches the categories-not-roster reality)

Change: Step 4 said 'add the new name to the domains list in meta-using-bitranox-skills'. That list is CATEGORIES
plus exemplars ('orientation only'; the injected available-skills list is the source of truth), and
repo-gate deliberately does not enforce the reverse direction - so there is no per-skill slot to fill.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read meta-using-bitranox-skills lines 107-121 (categories + exemplars, explicitly orientation
      only) and repo-gate's check_skills_index comment - the instruction sends an agent to edit a
      section with no slot for it
- [x] GREEN: step 4 now says to touch the list ONLY if the new skill's prefix is not already covered
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
