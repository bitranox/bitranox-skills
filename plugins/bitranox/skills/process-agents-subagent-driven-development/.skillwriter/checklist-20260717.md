# skill-writer checklist - process-agents-subagent-driven-development (2026-07-17, the advantage no longer contradicts the Never list)

Change: 'Parallel-safe (subagents don't interfere)' is listed as an advantage while Red Flags says 'Never:
Dispatch multiple implementation subagents in parallel (conflicts)' - opposite claims about the same act.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read line 429 against line 462: one says parallel-safe, the other forbids parallel implementers
- [x] GREEN: restated as context-isolated per task, explicitly not a licence to run implementers concurrently
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
