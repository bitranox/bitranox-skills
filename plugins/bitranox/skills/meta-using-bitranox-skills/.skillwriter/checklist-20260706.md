# skill-writer checklist - meta-using-bitranox-skills (2026-07-06, C5 roster trim)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] RED: roster enumerated ~40 names duplicating the available-skills list (drift-prone;
      gate forced every-skill-listing)
- [x] Change: categories + exemplars (~8 lines); "available-skills list is the source of truth";
      repo-gate check_skills_index relaxed to one direction (stale names only)
- [x] Pre-trim equivalence baseline: 3/3 probe tasks invoked the expected domain skill
      (files-edit-yml, compuse-bash, write-humanize-en) under installed 5.40.0
- [x] Trim committed (C5b, 5.42.4) under the relaxed gate
- [x] Post-trim equivalence: 3/3 (files-edit-yml, compuse-bash, write-humanize-en) - matches
  the pre-trim baseline; no revert needed. C5 closed.
- [x] Security scan: prose-only diff, clean

# skill-writer checklist - meta-using-bitranox-skills (2026-07-06, roster review wave 3)

- [x] Change: superpowers credit line + THIRD_PARTY_NOTICES entry added (verified upstream roster: obra/superpowers ships the ancestor; MIT notice now travels with the copy)
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent wave 6/6 (changed descriptions incl. two near-decoy discriminations)
- [x] Security scan: prose/frontmatter edits + file removals, no secrets/paths/PII
