# Review checklist 2026-11-05: the prune-run sentences in meta-skill-ab-test's SKILL.md

Change: three added lines after the `prune-run` sentence: it also removes, by exact path, a
worktree an arm registered itself under `arms/` (a parallel node's) with its branch, and a run dir
must not be deleted by hand because it can hold the pinned plugin checkout. The description is
untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024);
      the frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`;
      the file is ASCII only.
- [x] "removes, by exact path, a worktree an arm registered itself under arms/, with its branch":
      executed. `test_prune_run_removes_a_worktree_the_arm_registered_under_its_own_home` registers
      `arms/r1-C/home/wt/node-8` on branch `node-8` and a foreign worktree outside arms/, runs
      `prune-run` (exit 0): the arm's worktree and branch are gone, the foreign worktree and its
      branch stay.
- [x] "a run dir can hold the pinned plugin checkout": observed on the live run, where
      `vnc-r2/plugin-pin` is a registered worktree of the skills repository that later runs start
      from; the sentence says to leave it.
- [x] Mutation-proved: with the new removal loop reverted to the previous `abtest.py`, the test
      goes RED (1 failed); restored, it passes and the whole skill suite is green (328 passed).

## Probes

- [x] RED/GREEN: two added sentences describing one executed behaviour and one observed fact;
      probe skipped, reason: the suite executes the behaviour.
