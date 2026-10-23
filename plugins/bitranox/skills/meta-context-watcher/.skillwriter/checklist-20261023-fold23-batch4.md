# skill-writer checklist - meta-context-watcher (fold of memory rules into the skill)

- [x] Change: 'What belongs in it' > 'How to verify' bullet (appended), and 'When you are the one
      READING a handover' (new paragraph after 'Never amend a stale handover'). Verified against
      ground truth: handover.prev.md is created by step 3 and kept out of commits/ignored ->
      meta-context-watcher/SKILL.md:200-207 ('copy it, and keep the copy out of commits (ignore it
      beside handover.md, or list it in .git/info/exclude)'). Step 7 forbids work after the handover
      -> SKILL.md:226-230, so the rule is framed as 'gate after steps 2 and 3, before step 4' (no
      post-handover work), not the hint's 'gate after the handover'. Existing How-to-verify text
      already forbids 'CI is green on HEAD' and allows quoting a result for an earlier sha ->
      SKILL.md:154-158; new text adds only the missing half (local gate voided by later, possibly
      gitignored writes).
- [x] Added after review: Procedure step 4 states when to run a gate whose result the handover
      quotes.
- [x] Claims the source contradicts were dropped or corrected; machine-local figures, private names
      and incident history were not carried over.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against the pre-edit snapshot (partial for scenario
      1). Only a verbatim quote from the snapshot counts, so context inherited from this machine
      cannot satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files, in four rounds: after the edit,
      after the first review's fixes, after the delta review's fixes, and a final round on the
      questions the last fixes touched. Every scenario was answered with a quote from the new text
      on both tiers in every round; no NONE.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or recorded below.
- [x] Gaps closed or declined: closed - the gate step now also sits in the Procedure (re-tested by
      quote-back on haiku and opus); declined - a gate that rewrites tracked files (git status shows
      it; the rule exists for writes nothing shows), edits during step 6 (a write to the handover
      itself, already written after the gate).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, repo file paths or reserved examples.
