# skill-writer checklist - coding-python-clean-architecture (2026-07-14, capability check on REVIEW-mode judgment)

- [x] Change: added a "Capability check (REVIEW / judgment)" note - spotting architecture/layer violations and the true-vs-accidental-duplication call is capability-sensitive, so run REVIEW mode on a pinned `sonnet` subagent (`opus` for large/high-stakes), or offer switch-model-or-continue if inline. Cites `process-agents-subagent-driven-development`. Prose-only; description unchanged.
- [x] Receipt held (this session)
- [x] RED (audit): the skill's REVIEW mode ran layer/duplication judgment inline with NO subagent/tier/switch-model language (unlike its siblings enforce-data-architecture-strict and performance-review). Representative live RED (haiku) for the delegate style: infra-proxmox gate run inline with no escalation; and this session's enhance-skill haiku RED silently missed a live OOM.
- [x] GREEN: identical delegate-style pattern to the infra-proxmox representative, where haiku under the edited text refused to run the judgment on itself and offered pinned-subagent delegation / switch-model.
- [x] CSO / description: unchanged - no rebuild; in sync.
- [x] Security scan: prose-only note; no secrets/paths/PII.
