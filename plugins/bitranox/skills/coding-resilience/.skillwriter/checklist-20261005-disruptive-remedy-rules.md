# skill-writer checklist - coding-resilience (2026-10-05, disruptive-remedy pattern, contrib C5)

New Patterns bullet: before automating a disruptive remedy (reboot, driver reload, service
restart), check whether past occurrences started during that same remedy, climb cheaper rungs
first, cap attempts per episode, and order refusal checks so each branch is reachable.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: pattern. Test approach: recognition/application - one question answered with a
      direct quote or NONE.
- [x] RED (pre-change text, pasted): "Before scripting an automatic reboot to clear a hang, what
      should be checked first?" - NONE; the existing Circuit-breaker bullet covers a failing
      DEPENDENCY, not a remedy that is itself the trigger.
- [x] GREEN (new bullet pasted): same question now answers with a direct quote ("check whether
      past occurrences STARTED during that same remedy").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
