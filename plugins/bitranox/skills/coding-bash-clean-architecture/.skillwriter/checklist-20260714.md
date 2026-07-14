# skill-writer checklist - coding-bash-clean-architecture (2026-07-14, capability check on REVIEW-mode judgment)

- [x] Change: added a "Capability check (REVIEW / judgment)" note - judging architecture/layer violations (I/O mixed with logic, wrong function placement) is capability-sensitive, so run REVIEW mode on a pinned `sonnet` subagent (`opus` for large/high-stakes), or offer switch-model-or-continue if inline. Cites `process-agents-subagent-driven-development`. Prose-only; description unchanged.
- [x] Receipt held (this session)
- [x] RED (audit): REVIEW mode ran the architecture judgment inline with NO subagent/tier/switch-model language. Representative live RED (haiku): the delegate-style gap is real (infra-proxmox gate run inline; enhance-skill haiku silently missed a live OOM).
- [x] GREEN: identical delegate-style pattern to the infra-proxmox representative live GREEN (haiku refused inline judgment, offered pinned-subagent delegation / switch-model).
- [x] CSO / description: unchanged - no rebuild; in sync.
- [x] Security scan: prose-only note; no secrets/paths/PII.
