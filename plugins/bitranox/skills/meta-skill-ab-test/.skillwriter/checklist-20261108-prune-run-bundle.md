# Review checklist 2026-11-08: prune-run writes branches.bundle (meta-skill-ab-test SKILL.md)

Change: the `prune-run` paragraph of SKILL.md gains one clause: before deleting, prune-run writes
every branch of the run (set-aside attempts and killed arms included, which an arm's own
`bundle.git` does not hold) into `<run dir>/branches.bundle`, and deletes nothing if that fails.
The description is untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024); the
      frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`; the file
      is ASCII only.
- [x] "writes every branch of the run into branches.bundle": executed.
      `test_prune_run_bundles_every_branch_before_deleting_them` adds a set-aside attempt branch
      beside the arm branches, runs `prune-run` (exit 0) and compares `git bundle list-heads` of the
      bundle with the branch list taken before: equal; a second prune with no branch left keeps the
      bundle and adds none.
- [x] "an arm's own bundle.git does not hold them": measured on the live run behind this change,
      where 62 branches existed and the per-arm `bundle.git` files held 45 of them.
- [ ] "deletes nothing if that fails": read from `cmd_prune_run`, which empties the branch list when
      `_bundle_branches` returns an error; NOT exercised by a test (a failing bundle write needs a
      fixture no existing test provides). The SKILL.md clause states it as designed behaviour.
- [x] Mutation-proved: with `abtest.py` reverted to the previous source the new test goes RED (no
      branches.bundle); restored, it passes and the whole skill suite is green (331 passed, 1 skipped).
