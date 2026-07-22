# skill-writer checklist - process-test-design (2026-07-22, single-layer-mutation-stays-green)

Change: added a Common-mistakes bullet - under defense in depth a single-layer RED mutation can
stay green because a LATER validation check rejects the same bad input, so the test looks like
coverage it lacks; mutate the whole defense stack in one mutation to prove the contract.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: a real observed failure - two control-queue tests stayed green with one check removed
      (a later bound absorbed the mutation), a third vacuous test shipped the same way
      (fact feedback-defense-in-depth-breaks-single-mutation-red). Without the rule, a green
      single-layer mutation reads as coverage and a vacuous test ships "verified".
- [x] GREEN: bullet names the symptom (green despite a real gap), the cause (a later layer
      absorbs it), and the fix (mutate the whole stack in one mutation; keep the redundant check).
- [x] Scope: universal test-design fact; the concrete instance was scrubbed to generic prose.
- [x] Security scan: prose only, no secrets/hosts/paths/private repo names.
- [x] CSO description: unchanged (a Common-mistakes bullet; existing triggers cover retrieval).
- [x] Token budget: one bullet.
