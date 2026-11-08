# skill-writer checklist - meta-adopting-external-skills (2026-11-06, anchor length and gate order)

Two wording fixes in Step 4's ledger paragraph:

- "anchored on the sentence that states it" becomes "anchored on a 20 to 200 character phrase of
  the sentence that states it (`add` refuses a longer or shorter anchor)".
- The paragraph comes after Step 4's first gate run, so it now ends with "Before that commit, run
  the gate again, `python3 plugins/bitranox/hooks/repo-gate.py --ci`: the run above came before
  the ledger existed, and the gate checks it."

Decisions: none - wording fixes inside the procedure recorded as d-20261106-4e1cc697; no rule added, removed or rejected

- [x] Receipt fresh; Step 0b `show meta-adopting-external-skills --kind rejected,removed --full`
      printed nothing (no rejected or removed entries). The anchored sentence "Record a `rejected`
      entry for each upstream part Step 3 deliberately left out" is unchanged:
      `skill_decisions.py check` reports 0 findings.
- [x] Not mirrored (`repo-gate.py --mirrors`).
- [x] Each finding verified against the file first (SKILL.md:144 and :123).
- [x] The length claim executed in a throwaway detached worktree: `add` with a 19-character anchor
      refused "anchors: 20 to 200 characters after normalising" (rc 1); with a 230-character
      anchor the same refusal (rc 1). The gate command is the one Step 4 already prescribes; it
      runs as this change's own final gate.
- [x] Re-probe on the final text, haiku x1 (anchor for a ~200-character sentence; the commands to
      the adoption commit): rejected the whole sentence as the anchor and quoted a 93-character
      phrase; listed the second gate run. Its gap "is the second gate run before or after the
      commit" was real ("both go in the adoption commit. Then run the gate again") and is closed
      by "Before that commit"; a second haiku re-probe on that final text put the gate before the
      commit, quoting it. Remaining gaps (what to do on a red gate, a commit pathspec) are
      declined as out of scope: generic gate and commit practice, not adoption-specific. No new
      undecided gap.
- [x] Width and fence check over the added lines printed nothing; ASCII only; history-phrase
      finder: no hit.
