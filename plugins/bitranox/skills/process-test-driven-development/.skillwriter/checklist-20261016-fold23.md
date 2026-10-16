# skill-writer checklist - process-test-driven-development (2026-10-16, fold23)

- [x] Change: "Verify RED - Watch It Fail" gains "New behaviour is a refusal?": assert the message
      or field, not only the exit code, because argparse's own unknown-flag exit 2 passes an
      exit-code-only test before the feature exists; run against pre-feature code and require RED.
- [x] Change: "Verify RED - Watch It Fail" gains "Defect is in a cleanup path?": a probe the
      cleanup makes succeed passes against the unfixed code; use a probe whose outcome the cleanup
      cannot change (an unsupported command, a malformed request) and confirm it reds unfixed.
- [x] Change: "Verify GREEN - Watch It Pass" gains "An existing test asserts the very behaviour a
      user reported as a defect?": replace it, say why its fixture missed the case, name the changed
      assertion in the commit message. Placed beside "Fix code, not test" / "Other tests fail?"
      because those lines otherwise steer toward bending the fix.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded
      the skill through the Skill tool before its first SKILL.md edit
- [x] RED (text check of the artifact): before this edit SKILL.md (`git show HEAD:`) had no text
      for the three rules: "cleanup path" 0 hits, "refusal" 0 hits, "user reported" 0 hits.
      Verifier gaps: "SKILL.md has no text about cleanup paths", "Missing: when the new behaviour is
      a refusal, assert the specific message or field and not only the exit code", "No line covers
      this case, and the nearest line in Verify GREEN, 'Fix code, not test', steers the agent the
      wrong way". Behavioural RED replaced on purpose because the rules are in the always-loaded
      memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): cleanup-path probe
      -> SKILL.md:141 "**Defect is in a cleanup path (reset, close, teardown, eviction)?** Ask what
      the probe does AFTER the cleanup runs." and :144-145 "Use a probe whose outcome the cleanup
      cannot change - an unsupported command, a malformed request - and confirm it reds on the
      unfixed source."; replace a test asserting the reported defect -> SKILL.md:202-203 "**An
      existing test asserts the very behaviour a user reported as a defect?** REPLACE it; do not
      bend the fix to keep it green or keep both tests." and :204-205 "name the changed assertion
      in the commit message"; refusal RED asserts the message -> SKILL.md:136-139 "**New behaviour
      is a refusal?** Assert the specific message or field, not only the exit code. ... (argparse
      exits 2) ... Run it against the pre-feature code and require RED."; contradictions: none in
      job
- [x] Gaps closed or declined: none
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
