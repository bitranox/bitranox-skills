# skill-writer checklist - compuse-git (2026-09-02, worktree GIT_DIR export, and info/exclude on a fork)

Change: two sections. A `git push` from a linked worktree exports `GIT_DIR` to its hooks, so a hook
that runs tests hands them the real repository. And on a checkout that pushes to a foreign remote,
private tooling belongs in `.git/info/exclude`, because a tracked `.gitignore` line is what makes
the file committable.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. Both lessons are already in this machine's memory
      store, so a behavioural baseline is contaminated and cannot fail honestly. Pre-change,
      `grep -c GIT_DIR` and `grep -c info/exclude` over SKILL.md both returned 0.
- [x] The coverage check was shown to be capable of firing: a control term (`git`) returned 59.
- [x] MEASURED, not asserted: four arms on git 2.53.0 with a pre-push hook logging its environment.
      Ordinary checkout push -> `GIT_DIR=unset`. Linked worktree push -> `GIT_DIR` set to
      `<main>/.git/worktrees/<name>`. The control arm is what makes the claim a difference rather
      than an observation.
- [x] Placement is load-bearing: the worktree section sits directly after the section that
      RECOMMENDS a per-session worktree, because that recommendation is what creates the trap.
- [x] Scope: shared - both are stock git behaviour, not this machine's layout.
- [x] Security scan: no hosts, IPs, credentials or real paths; the one path shown is
      `<main>/.git/worktrees/<name>`.
- [x] CSO description: unchanged; both sections fall under existing triggers.
- [x] Token budget: reference skill, two sections added, body still an index of concrete cases.
