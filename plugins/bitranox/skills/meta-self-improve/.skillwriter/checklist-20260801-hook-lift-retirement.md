# skill-writer checklist - meta-self-improve (2026-08-01, retiring a lifted local hook)

Change: the escalation ladder's guard step told you to lift a globally-useful local guard into the
plugin's `hooks/` and stopped there. It never said what happens to the local copy. Ships with 5.131.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] The gap is DOCUMENTARY and provable by quoting, so it is verified by reading rather than by a
      subagent baseline: the ladder ends at "a globally-useful guard belongs in the shared plugin's
      `hooks/` and MUST propagate upstream - local-only `~/.claude/hooks` is the classic loss."
      Nothing after that mentions the local copy, so following the skill exactly leaves it armed.
- [x] The failure is MEASURED, twice on one machine, which is stronger evidence than a baseline
      opinion would have been:
      - `block_pgrep_self_match.py` (local, Jul 16) vs the plugin's `block-pgrep-self-match.py`
        (Jul 29). Both registered, both firing; the local one lacked heredoc stripping, so it
        blocked commands whose TEXT merely mentioned the footgun - it twice blocked writing the
        documentation for the very rule it guards.
      - `tell-sweep.sh` (local, Jun 24) vs the plugin's `tell-sweep.py` (Jul 2), fully redundant.
- [x] Why half is worse than neither is stated, because each half fails differently: file-only
      removal leaves a registered hook erroring on every matching call; entry-only removal leaves an
      armed file for the next stale runbook line.
- [x] The prove-coverage-first requirement is included, since the obvious assumption - the newer
      copy is a superset - is exactly what would have made this dangerous. Both retirements here
      were preceded by a 6-case comparison feeding identical synthetic hook events to both copies,
      checking the cases that must fire AND the ones that must not.
- [x] Routed to the ladder rather than to `meta-skill-writer`: authoring a cross-platform hook is
      that skill's job, but the LIFT is this ladder's step, and the retirement completes it.
- [x] Cross-reference kept accurate: `update-config` is named as the HOST skill it is.
- [x] No session narrative or private provenance in the skill text; no machine paths added.
