# skill-writer checklist - process-debug-systematic (2026-07-14, add switch-model fallback to Phase 3 reasoning)

- [x] Change: Phase 2/3 already offloads the bounded search to a `sonnet` subagent and names the main `opus` agent for hypothesis/root-cause reasoning, but gave no fallback if the session is NOT on opus. Added: this deep reasoning is capability-sensitive, so on a lesser tier offer switch-model-or-continue or hand the root-cause step to a pinned `opus` subagent. Prose-only; description unchanged.
- [x] Receipt held (this session)
- [x] RED (audit): the Phase 3 note assumed `opus` with no action for a lesser session tier - a weak session model does the capability-critical root-cause reasoning inline with no escalation offered.
- [x] GREEN: same inline-judgment pattern as the receiving-code-review representative live GREEN (haiku declined to self-judge a capability-sensitive call and offered sonnet/opus delegation / switch-model).
- [x] CSO / description: unchanged - no rebuild; in sync.
- [x] Security scan: prose-only note; no secrets/paths/PII.
