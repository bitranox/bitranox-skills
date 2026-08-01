# skill-writer checklist - process-review-verification-before-completion (2026-08-01, design conflict resolved)

Source: a design conflict surfaced by the clean-room sweep and decided by the operator, one at a
time, on the verbatim text of both sides. Ships with plugin 5.133.0.

- [x] CONTRADICTION inside one paragraph: the verifier subagent was told to "re-run the commands"
      and, one sentence later, "(Command execution itself stays in the main agent.)"
- [x] DECIDED: the verifier RUNS the commands itself. The parenthetical is gone, and the reason is
      now in the text - a verifier handed the main agent's output inherits exactly the optimism the
      section opens by saying you cannot check in yourself, so a misreported result is precisely
      what would survive.
- [x] Consistent with what this session measured repeatedly: re-running is what caught the wrong
      `curl -I` claim, the strip script's real behaviour, and rpyc's actual `--host` default. In
      each case reading the document agreed with the document.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Both sides were quoted verbatim to the operator before the choice; the decision is theirs and
      the reasoning is recorded here rather than inferred later from the diff.
- [x] No session narrative or private provenance added; no machine paths added.
