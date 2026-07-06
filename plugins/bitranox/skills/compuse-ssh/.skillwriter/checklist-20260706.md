# skill-writer checklist - compuse-ssh (2026-07-06, roster review wave 4)

- [x] Change: description gains the auth/host-key triggers (password prompt, host key verification failed, remote host identification changed, key setup) - 40% of the body previously had no matching trigger
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent wave 4/4 (semantically changed descriptions)
- [x] Security scan: prose/frontmatter edits + one test file added, no secrets/paths/PII

# skill-writer checklist - compuse-ssh (2026-07-06, root-cause-any-failure + retroactive 5.52.0 review)

- [x] Change: new Quick-reference row "ANY remote command fails - ROOT-CAUSE it" (exit 255 = ssh itself vs any other code = the remote command; evidence chain stderr -> `ssh -v` probe -> remote state/logs; flaky-network is a hypothesis to test, blind retry double-fires a mutating command); description gains the exit-255 and stalled/failed-download triggers
- [x] Retroactive review of the 5.52.0 rows (detached download + download root-cause), which shipped without a skill-writer run: content verified technically sound and consistent; covered by this change's GREEN test (Q3/Q4)
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED: sonnet baselines (choice-framed AND open-ended pressure scenarios) would not violate - discipline internalized at this tier; change reclassified REFERENCE-shaped (the retrieval gap was the failing test: prior text had no 255 semantics, no general-failure evidence chain)
- [x] GREEN: fable retrieval test 5/5 with correct row citations
- [x] Discovery test: fable subagent routed "exit 255" and "download sitting at 0 bytes" tasks to compuse-ssh against 5 decoy skills (4/4 overall)
- [x] Security scan: prose/frontmatter edits only, no secrets/paths/PII
