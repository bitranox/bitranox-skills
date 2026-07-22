# skill-writer checklist - meta-dream-tree (2026-07-22, deliver-contributions-at-dream-end)

Change: step 10 now frames delivering queued contributions as a REQUIRED end-of-dream action, adds
"verify each against the CURRENT skill content first - drop already-shipped", and replaces the loose
"anything still pending stays queued and is surfaced next session" with: leave one queued ONLY when
it needs user input or the mode is off, else deliver this run per the mode.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the same stop-at-queue loophole lives in tree step 10 (line: "anything still pending stays
      queued and is surfaced next session"), which reads as "leaving them is fine" - the exact
      failure that shipped nothing on the crosstree-deep run (fact
      feedback-at-a-dream-s-end-deliver-queued-contributions-respecting-the-mode-do-not-stop-at-queuing).
- [x] GREEN: step 10 requires delivery per mode, verify-first, and qualifies "still queued" as the
      exception - consistent with the crosstree fix.
- [x] Scope: applies to every tree dream; mode semantics unchanged, only tightened.
- [x] Security scan: prose only, no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit).
- [x] Token budget: reworded one existing step.
