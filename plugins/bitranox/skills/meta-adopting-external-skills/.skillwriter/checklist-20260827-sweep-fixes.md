# skill-writer checklist - meta-adopting-external-skills (2026-08-27, sweep fixes)

The sweep filed four DANGLING/WRONG findings against this skill. All four are false positives, and
all four are symptoms of one real omission, which is what is fixed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] Rejected: `plugins/bitranox/.claude-plugin/plugin.json`, `plugins/bitranox/hooks/repo-gate.py`,
      the `adopt_skill.py` invocation and `CONTRIBUTING.md` were each reported as resolving to
      nothing. They all resolve in a marketplace-repo CHECKOUT, which is the only place adoption can
      happen: `CONTRIBUTING.md` is at the repo root, and `adopt_skill.py::_find_repo_root` searches
      upward for `plugins/bitranox/.claude-plugin/plugin.json`, so the script is repo-scoped by
      construction.
- [x] Accepted root cause: the skill never STATED that precondition, which is why four independent
      reviewers each reported a different symptom of it. A new opening section names it and says
      what to do when standing in an install instead.
- [x] Paths left as they are - they are correct for the stated location.
