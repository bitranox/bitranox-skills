# skill-writer checklist - compuse-git (2026-07-17, the pre-commit verify block includes the check its own prose calls required)

Change: The 'verify state (cheap, deterministic)' code block had 3 lines; the paragraph immediately after says
`git status --short` is required because the branch-guard does NOT catch already-staged sibling files.
The block reads as the complete procedure, so the sweep-risk check got skipped.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read lines 109-122: the prose names a 4th required check that the enumerated block omits
- [x] GREEN: added `git status --short` to the block with the reason inline
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
