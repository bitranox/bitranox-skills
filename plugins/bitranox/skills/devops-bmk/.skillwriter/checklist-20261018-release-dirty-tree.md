# skill-writer checklist - devops-bmk (2026-10-18, release-dirty-tree)

- [x] Change: section 3 gains one bullet under "`release` does not bump": `release` counts only
      tracked changes as dirty; on its "Working tree not clean" refusal an unrelated edit is set
      aside (copied, or stashed under a name and popped by the `stash@{N}` listed under that name)
      and restored after the release, never committed to get past it, because the tag lands on
      HEAD and that commit never ran in CI; an edit that belongs in the release, bmk's own Makefile
      or floor churn included, is committed with git and those paths, pushed, and released only
      once CI is green, since `release` never checks CI. One Troubleshooting row points the
      refusal message at that bullet.
- [x] Every claim checked against bmk source (`_release.py`): `_ensure_clean` runs `git diff
      --quiet` and `git diff --cached --quiet` only, so untracked files pass; it prints the quoted
      refusal; the tag is `git tag -a` with no commit argument (HEAD); the module makes no CI call.
      The `rel` pipeline in `registry.py` is the single `release` stage, and `_ensure_bmk` only
      upgrades bmk, so `make release` itself writes no tracked file before the check.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED, behavioural: five arms on the pre-change section (two haiku and one opus multiple
      choice, two haiku open-ended) all chose to set the edit aside, so the behavioural RED did not
      fail. Every arm reported the same gap: the text never says what to do on the refusal, whether
      untracked files count, or who waits for CI, and each answer was the agent's own inference.
- [x] RED route recorded: `redcheck --corpus-cascade` reported INHERITED COVERAGE on two documents;
      reading them, both are term overlaps (the shared-stash index line, a merge-in-a-worktree
      fact), neither states the release rule. The behavioural arm is replaced by a text check of
      the artifact: a grep over every installed skill and every memory fact found the rule only in
      the fact this change folds.
- [x] GREEN quote-back on haiku and opus, five questions (unrelated edit, Makefile and floor
      churn, untracked file, getting a stash back, where the tag lands after committing): every
      answer correct and quoting the governing sentence; quotes substring-checked against the
      file (5 of 5).
- [x] Gaps closed after GREEN: "pop it by that name" (git stash pop takes a ref, so the text now
      says to pop the `stash@{N}` that `git stash list` shows under that name); who waits for CI
      (`release` never checks it, so the reader waits); how to commit churn without `push`'s
      `git add -A` (git with those paths). Re-tested on haiku for the two questions the fix
      touched: both answered with quotes.
- [x] Gaps declined: how to check CI (generic, outside bmk), where to copy an edit aside and what
      to do if a stash pop conflicts (git, not bmk), whether churn needs a version bump (it does
      not change the version), urgency (no step relaxes for it), and a re-run of `release` pushing
      an up-to-date branch (harmless).
- [x] GREEN diffed against RED both ways: RED's set-aside answers all survive; GREEN adds the
      tracked-only rule and the churn path RED had to guess.
- [x] Description measured: unchanged (440 characters).
- [x] Mirror: byte-identical to the tool repo's `skills/devops-bmk/SKILL.md`.
- [x] Security scan: prose only; no secrets, hostnames, private paths or addresses.
