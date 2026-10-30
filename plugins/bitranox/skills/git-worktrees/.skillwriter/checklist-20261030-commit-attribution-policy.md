# skill-writer checklist - git-worktrees (2026-10-30, commit attribution policy)

- [x] Change: "Bringing an isolated subagent's work back" now says, before the cherry-pick, to
      check the subagent's commit messages (`git log --format=%B <base>..<branch>`) against the
      repo's commit-attribution policy, because a cherry-pick carries them over unchanged, and to
      reword a violation on its branch first, pointing at
      bitranox:process-agents-subagent-driven-development, File Handoffs, for the policy and the
      checks. The rule is neutral: the skill names no policy of its own. The brief that carries
      the policy is written by the dispatching skill, not here.
- [x] Receipt held (`skill_receipt.py check meta-skill-writer`: fresh), skill loaded by the editing
      agent through the Skill tool.
- [x] Text check on the pre-edit file (`git show HEAD:`): `grep -ciE
      'attribution|co-authored|generated with'` printed 0.
- [x] RED (pre-edit excerpt of the paragraph; one combined probe over four skills, haiku): Q2 (what
      is checked about commit messages before picking) NONE: "The only check is: 'Cherry-pick its
      commits onto your branch and re-run the full suite there ...'. That is a test check.
      Cherry-pick carries the subagent's commit message onto your branch unchanged, and the excerpt
      does not tell you to look at it."
- [x] GREEN 1 (post-edit excerpt plus the SDD File Handoffs bullets, declared the text under test),
      haiku and opus (effort medium): both quoted "Before you pick, check its commit messages ...
      against the repo's commit-attribution policy: a cherry-pick carries them over unchanged" and
      applied the SDD forbid and require commands over `<base>..<branch>`. Opus reported that the
      paragraph said "check" without a remedy.
- [x] Fix: "so reword a violation on its branch first" added to the same sentence.
- [x] Re-probe on the final text, haiku and opus (effort medium): Q3 (a violating commit on the
      subagent's branch) both: reword on its branch, then cherry-pick, then the full suite, quoting
      "a cherry-pick carries them over unchanged, so reword a violation on its branch first". No
      new undecided gap.
- [x] Gaps declined: Q1 (what the brief says) is NONE here by design, since the dispatching skill
      writes the brief; reword mechanics and where to run them (owned by bitranox:compuse-git);
      that a reword changes the commit shas (the paragraph already says to pick the branch's
      commits after the reword, and dispatching-parallel's "Pick the branch TIP" covers stale shas).
- [x] Tiers and cells: RED 1 (haiku) x 2 questions; GREEN 2 (haiku, opus) x 2; re-probe 2 x 1.
- [x] Added lines: no history-finder hit, no address or home path, ASCII only; description
      unchanged.
- [x] Tests: `plugins/bitranox/skills/git-worktrees/tests` ran green with the SDD skill's tests
      (227 passed); the hooks suite ran green (counts in the report).
