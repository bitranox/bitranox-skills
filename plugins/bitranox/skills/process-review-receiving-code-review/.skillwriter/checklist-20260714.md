# skill-writer checklist - process-review-receiving-code-review (2026-07-14, capability check on the EVALUATE judgment)

- [x] Change: added a "Capability check (EVALUATE)" note - deciding whether external feedback is technically sound for THIS codebase (and whether to push back) is capability-sensitive, so on a lesser tier delegate the EVALUATE judgment to a pinned `sonnet`/`opus` subagent or offer switch-model-or-continue. Cites `process-agents-subagent-driven-development`. Prose-only; description unchanged.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED (audit): the skill's EVALUATE step had NO subagent/model-tier/switch-model language - a weak session model self-judges plausible-but-wrong feedback with no escalation.
- [x] GREEN (live, haiku): under the edited skill, given a plausible-but-wrong review claim (lru_cache "not thread-safe"), haiku declined to self-judge ("I should not self-judge this EVALUATE step") and offered to delegate to a sonnet/opus subagent or defer to the user.
- [x] CSO / description: frontmatter unchanged - no rebuild; in sync.
- [x] Security scan: prose-only note; no secrets/paths/PII.
