# skill-writer checklist - meta-dream-crosstree (2026-07-22, deliver-contributions-at-dream-end)

Change: step 7 now makes delivering queued skill/hook contributions a REQUIRED end-of-dream action
per the mode (self-PR in propose, commit-or-PR in auto, skip in off), adds "verify each against the
CURRENT skill content first - drop already-shipped", and reframes leaving one queued as the
exception (needs user input or off-mode). Step 8 report line matches.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: a real observed failure - THIS crosstree-deep run queued 5 contributions, reported "5
      queued, awaiting go", and stopped; nothing shipped until the user manually said "do the
      queued skill contributions" a later turn, at which point 2 of 5 turned out already shipped
      in-skill (the verify-first step that was missing). Fact
      feedback-at-a-dream-s-end-deliver-queued-contributions-respecting-the-mode-do-not-stop-at-queuing.
- [x] GREEN: step 7 states deliver-is-required + verify-against-current + drop-already-shipped, and
      "still queued" is only for blocked/off-mode; step 8 report matches, closing the loophole.
- [x] Scope: applies to every crosstree/-deep dream; mode semantics unchanged, only tightened.
- [x] Security scan: prose only, no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit; triggers cover retrieval).
- [x] Token budget: a few clauses added to two existing steps.
