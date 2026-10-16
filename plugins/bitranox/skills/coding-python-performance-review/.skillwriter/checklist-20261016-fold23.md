# skill-writer checklist - coding-python-performance-review (2026-10-16, fold 23)

- [x] Change (recorded BEFORE figure): new paragraph in "Validating a claim or comparing
      before/after", after the `compare_performance.py` bullet - when a recorded BEFORE figure
      exists, run the probe against the unfixed code first and require it within an order of
      magnitude; an early-return probe is fast in both arms; count calls into the hot function to
      find the guard; comment in the test why its input has that shape.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit "Nothing in SKILL.md or the scripts tells an
      agent to run the probe against the UNFIXED code first and require that BEFORE result to land
      within an order of magnitude of the recorded figure". Behavioural RED replaced on purpose
      because the rule is in the always-loaded memory index of the authoring machine (inherited
      coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): recorded BEFORE
      figure -> SKILL.md:104-109 "When the defect you are fixing already has a recorded BEFORE figure
      ... run your probe or test against the UNFIXED code first and require it to land within an
      order of magnitude of that figure before you trust your AFTER number. A probe that hits an early
      return is fast in both arms ... count calls into the hot function to find the guard that
      returns early"; contradictions: none in the job; step-4 scan of SKILL.md: no hit
- [x] Gaps closed or declined: none
- [x] Description measured: unchanged (360 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
