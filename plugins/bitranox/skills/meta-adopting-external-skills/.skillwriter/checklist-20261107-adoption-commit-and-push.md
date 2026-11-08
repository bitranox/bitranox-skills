# skill-writer checklist - meta-adopting-external-skills (2026-11-07, adoption commit and push)

The skill contradicted itself: Common mistakes listed "Letting the helper or yourself commit,
push, or uninstall anything", while Step 4 had the agent make "the adoption commit". Two user
decisions (2026-11-07) settle it:

- The agent makes the adoption commit with its bump and pushes it; the helper never commits or
  pushes; nobody uninstalls anything.
- Upstream-first stays: the adoption is ONE commit on its own worktree branch, pushed to master
  only once upstream stalls or declines, after `bump_version.py --rebase`; if upstream takes the
  change, the branch and its worktree are deleted.

Changes: Step 4 gains the branch sentence; Step 5 gains "Ship it from the branch, or delete the
branch"; the Common mistakes line is rewritten and one mistake added.

Decisions: d-20261107-0c591a38, d-20261107-a947e7a8

- [x] Receipt fresh; Step 0b `show meta-adopting-external-skills --kind rejected,removed --full`
      printed nothing. The live rule d-20261106-4e1cc697 (adoption records its decisions before
      the adoption commit) agrees with the change; `skill_decisions.py check` reports 0 findings
      after the edit and after the two new entries.
- [x] RED as a text check of the pre-edit file (the old version is installed, so a no-skill
      behavioural arm would load it): line 20 "Adoption commits to that repo", lines 140-156 "both
      go in the adoption commit", line 173 "Letting the helper or yourself commit, push, or
      uninstall anything"; no line said when or whether to push.
- [x] GREEN round 1, haiku and opus, on the first wording (commit is yours, push once Step 5 says
      to ship): both quoted it for Q1-Q4 and found no contradiction. Opus reported that the commit
      would wait unpushed indefinitely, could lose its version number, and had no fate if
      upstream accepted. That is a case the first ruling did not cover, so it went to the user
      (second decision above) instead of being decided in the text.
- [x] Executed before the re-probe: in a throwaway detached worktree, a commit bumping 10.21.0 to
      10.22.0 on the 10.21.0 commit, with origin/master already at 10.22.0. `bump_version.py
      --rebase --no-fetch` printed "renumbered onto origin/master at 10.22.0 -> 10.22.1", left
      HEAD's parent equal to origin/master, and wrote `## [10.22.1]` into CHANGELOG.md; a second
      run refused "nothing was taken, an ordinary rebase will do" (rc 1). Worktree and its backup
      ref removed afterwards.
- [x] GREEN round 2, haiku and opus, on the full final text (Q1 who and which branch, Q2 when,
      Q3 version taken, Q4 upstream merged, Q5 contradictions): every answer a direct quote of
      the new text, Q5 NONE in both. Gaps closed after it: where the push goes ("to master"),
      which files `--rebase` renumbers, and removing the worktree with the branch. A haiku
      re-probe of the final Step 5 quoted all three; no new undecided gap.
- [x] Gaps declined: "stalls" has no time limit (the user's decision states this change does not
      fix it); push mechanics, CI watch and which checkout to push from (the repo's CLAUDE.md
      "Do not rewrite history" and its pre-push hook section own them); how the upstream PR is
      opened and a decline detected (owned by meta-self-improve, "Propagating skill (or hook)
      improvements upstream", REQUIRED in Step 5); the exact number `--rebase` picks (the jig
      decides and prints it, measured above); Step 4's "ship passing tests" means include them,
      ordinary wording that predates this change.
- [x] Not mirrored (no twin in MIRRORED_SKILLS for this skill).
- [x] Width and fence check over the added lines printed nothing; ASCII only; history-phrase
      finder: no hit.
