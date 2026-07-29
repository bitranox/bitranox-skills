# skill-writer checklist - process-review-enhance-code-quality (2026-07-29, skill claims)

Change: extend the shipped-skill check from coverage to truth - re-verify absence claims ("no X
yet", "not supported", "only on Linux") and contract claims ("never raises", "always returns",
exit codes) against the code each review. Shipped in plugin 5.101.1.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, from the user asking whether the review would have caught the skill gaps at all. Reading
      the skill answered it: before today it referenced five other skills and none of them reviews
      skills, so the answer was no. The coverage check added earlier today closes the omission
      half. This entry closes the other half, which the check did not reach.
- [x] The gap is precise, and was verified rather than assumed: the original failure - a skill
      asserting "no MAC, ARP or port-scan surface yet" two releases after those shipped - IS caught
      by the coverage check, but only incidentally, because that skill also omitted the names. A
      skill that names every symbol and describes it wrongly passes coverage completely.
- [x] Not hypothetical: the current ipscout skill carries two "never raises" claims, which an agent
      writes error handling against. Nothing verified them before this.
- [x] Two categories named rather than "check the claims", because they fail differently: an
      absence claim rots into steering an agent AWAY from a working feature, which is worse than
      silence; a contract claim is what a caller's error handling is built on.
- [x] Honest about mechanism: this half is read-and-verify, not a script, and the skill says so
      rather than implying a check that cannot exist. It gives the grep as the starting point and
      says where the SEVERE findings come from, so the effort lands in the right place.
- [x] The "is it pinned by a test?" question is included, since an unpinned load-bearing contract
      claim is a finding on its own.
- [x] Scope: shared/general - applies to any repo shipping a skill.
- [x] Security scan: prose only, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body addition, frontmatter untouched).
- [x] Token budget: one sub-section under an existing always-on check.
