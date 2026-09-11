# skill-writer checklist - process-test-design (2026-09-12, flake reproduction)

Two gaps, landed together because they are complements: what a test should wait on, and how to
reproduce a flake once it has one.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. The test is a coverage check plus a quote-back; the underlying
      claims are already measured and the measurements are carried into the text.
- [x] Scope: two sections added ahead of the clean-environment section, inside the determinism
      part of the skill.

## RED
- [x] Behavioural RED not used: both lessons are already pointer lines in this machine's
      always-loaded memory index. `redcheck --corpus-cascade` returned clean, which means NOT
      CAUGHT rather than absent, so the coverage check against the file is the evidence.
- [x] Coverage RED with a positive control: control `order-independent` 3 hits; slow-the-clock 0
      hits; starvation 0 hits; lands-last 0 hits.

## GREEN
- [x] Same instrument after the edit: control 3, slow-the-clock 2, starvation 3, lands-last 2.
- [x] Quote-back: "A flake reproduces under the pressure that matches its MECHANISM, and the two
      mechanisms need opposite apparatus", with the task-race arm under CPU starvation and the
      timer-race arm needing the clock it races slowed instead.
- [x] The starvation arm carries its working range, so a finding past roughly 2.3x competitors
      is checked against the unstarved arm rather than believed.
- [x] Both arms are required to run through the real test entry point, because a standalone
      probe can stub out the path that fails and then passes whatever the code does.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] Measurements are stated as counts, with no machine, host or project named.
- [x] Frontmatter untouched.
