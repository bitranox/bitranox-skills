# skill-writer checklist - meta-dream-tree (2026-07-15, maintenance sweep no longer rewrites hooks merely over the 350 soft cap)

- [x] Change: the Voice+firing maintenance sweep (step 6) queued a hook for rewrite if it was "over the 350 soft cap". Reframed to queue only when it FAILS the trigger-first lint (`hook_missing_trigger`), OR exceeds the 500-char HARD cap (`cap_hook` would truncate it), OR fails the firing check. Explicit: do NOT rewrite a hook merely for exceeding the 350 SOFT cap - a complete trigger-first hook may run up to the hard cap. Mirrors the meta-self-improve reframe (fix-shared-bug-in-all-siblings).
- [x] Receipt held (this session)
- [x] RED (audit + shared demonstration): the sweep listed "over the 350 soft cap" as a rewrite trigger, so a complete hook over 350 would be needlessly rewritten - the same soft-treated-as-hard error demonstrated LIVE on the meta-self-improve deliverables (haiku trimmed a complete 402-char hook to ~314).
- [x] GREEN: same reframed rule as the verified meta-self-improve change (soft cap advisory; act only on the 500 hard cap / trigger-first / firing failures), so the sweep no longer rewrites a hook just for the soft cap.
- [x] Descriptions unchanged - no rebuild. Security scan: prose-only; no secrets, paths, or PII.
