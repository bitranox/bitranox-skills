# skill-writer checklist - meta-context-watcher (2026-08-27, sweep fixes)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] Two figures were stated as bare current fact: the accuracy-degradation thresholds and the 83%
      auto-compact point. The plugin's own `hooks/context-watcher.py` labels the first "read
      second-hand from a summary" and attributes it to Chroma's 2025 study; the second is product
      behaviour that moves between releases. The skill now carries that provenance and says to
      treat both as an order of magnitude rather than thresholds to tune against.
- [x] Figures themselves left unchanged - the fix is the missing anchor, not the numbers.
