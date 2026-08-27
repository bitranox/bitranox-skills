# skill-writer checklist - meta-claude-hooks (2026-08-27, sweep fixes)

The Notification event's matcher-value list was missing three values upstream now documents. The
SKILL.md change is the one line the stamp tool owns, rewritten by that tool.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a factual omission, so the RED is a check against the
      upstream document rather than a pressure scenario.
- [x] RED came from this skill's OWN instrument, not a hand-rolled check: `hookdoc_stamp.py check`
      returned verdict STRUCTURAL, naming exactly `quota_auto_resume_fired`,
      `quota_auto_resume_stale` and `quota_auto_resume_disabled` as added upstream table keys.
- [x] GREEN: both places that enumerate the values now carry all three, with the CLI floor (2.1.234+)
      that gates them. Both were needed - `references/configuration.md` holds the matcher table and
      `references/events.md` repeats the list in the event section, and a reader consults either.
- [x] `coverage` passes (31 events, 65 required names), which is what gates a re-stamp.
- [x] Stamp refreshed with `stamp --write`; `check` now returns CURRENT, rc 0. Documented coverage
      moved from CLI 2.1.236 to 2.1.246.
- [x] The SKILL.md "Reference baseline" line is generated: rewritten with `baseline --write`, not by
      hand, and its test passes.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] REVISED after the decision review: the first stamp was premature. Re-stamping asserts our
      references match upstream, but `coverage` only checks that stamped NAMES appear, so it cannot
      see a behavioural note about a name we already document. Diffed the 2.1.236 -> 2.1.246 window
      by fetching both upstream pages and listing every version marker in them.
- [x] The window holds exactly two items. `classifierContext` (2.1.236) was already covered, in
      `io-contract.md` - the previous stamp was honest. The 2.1.246 item was NOT: in terminal
      sessions `permission_prompt` now also fires for a sandboxed command's network request. Added
      to `events.md`, with the point a reader needs - on an older build the hook sees nothing, so
      its silence is not evidence the request did not happen.
- [x] Re-stamped after that fix. The stamp hashes UPSTREAM, so our addition does not move it; the
      gap was ours alone and closing it is what makes the CURRENT verdict true rather than asserted.
