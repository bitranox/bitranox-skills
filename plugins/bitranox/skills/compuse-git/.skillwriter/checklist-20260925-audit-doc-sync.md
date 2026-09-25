# skill-writer checklist - compuse-git (2026-09-25, audit behaviour sync)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every changed line states what a script now does after the
      skill-script audit fixes, so the RED is a ground-truth check of the old text against the
      code, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft. The artifact checks are immune.
- [x] RED, ground truth: the old text said `git_state` "exits non-zero if ANY repo is out of
      sync" and scanned "every .git repo below a dir". The script now distinguishes exit 1 (out
      of sync) from exit 2 (incomplete: unreadable repo, missing or empty `--root`), reports a
      gone upstream and each staged file, and finds repos whose `.git` is a FILE (linked
      worktrees, submodules); pinned by `compuse-toolbox/tests/test_git_state.py`, and
      `git_state --root <missing>` was executed and exits 2.
- [x] GREEN: a haiku probe given only the new text answered eleven retrieval questions across
      the changed rows and paragraphs (procsig, pushcheck, mutation_arm, fleet_ssh, adjudicate,
      claim_check, ci_wait, transcript_index, git_state, the SDD report name, the session-review
      part loop) all correctly, each with a direct quote of the governing sentence.
- [x] Skill gaps from GREEN decided: (a) the claim_check unreadable-path sentence needed chaining
      to the BROKEN sentence before it - CLOSED, it now names BROKEN itself; (b) no full command
      line shown for a three-path `--scp` - DECLINED, the flag syntax states the arity.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; ASCII only.
- [x] Present tense, no session narrative, no private provenance.
