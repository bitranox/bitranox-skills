# skill-writer checklist - meta-using-bitranox-skills (2026-07-06, C5 roster trim)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] RED: roster enumerated ~40 names duplicating the available-skills list (drift-prone;
      gate forced every-skill-listing)
- [x] Change: categories + exemplars (~8 lines); "available-skills list is the source of truth";
      repo-gate check_skills_index relaxed to one direction (stale names only)
- [x] Pre-trim equivalence baseline: 3/3 probe tasks invoked the expected domain skill
      (files-edit-yml, compuse-bash, write-humanize-en) under installed 5.40.0
- PENDING (gate on the trim commit): post-trim equivalence - the SAME 3 probes after the
  next marketplace update must be 3/3, else REVERT (equivalence_probe.py post)
- [x] Security scan: prose-only diff, clean
