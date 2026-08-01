# skill-writer checklist - meta-dream-nap (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.128.0.

- [x] DANGLING: "propose-first per the removal policy" named no home, and nap cites only two files.
      The policy is the `## Removal = obsolete-pruning + manual` section of
      `meta-dream-tree/references/dream-passes.md`; the reference now says so.
- [x] Verified before writing the pointer, and my first check used too narrow a pattern - grepping
      the literal phrase "removal policy" missed the heading, which spells it "Removal =". The
      pointer is correct; the near-miss is recorded because a wrong cross-reference is exactly the
      defect class this audit exists to remove.
- [x] The toolbox-pass finding is recorded as open: whether a nap should run it is a scope decision.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every QUOTE checked against the real file; every behavioural claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths added.
