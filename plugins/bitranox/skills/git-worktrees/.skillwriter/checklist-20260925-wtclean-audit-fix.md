# skill-writer checklist - git-worktrees (2026-09-25, wtclean audit fixes)

Change: the Step 4 text is corrected where `scripts/wtclean.py` changed documented behaviour. The
old text said `.worktrees/wt-my-feature` still looks for `<base>/wt-my-feature-target` - that is
the cache of a different worktree, `<base>/wt-my-feature`, and `--apply` deleted it. The section
now states that the prefix is kept inside the project-local directories, that a missing
`--cache-dir` is refused, that the home directory is refused, that bare and `--separate-git-dir`
repositories work, that the removal has no timeout, and that a partial size reads `at least`.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] Route: a TEXT CHECK of the artifact against the script's executed behaviour. These are
      reference corrections, so the evidence is the script run, and every sentence added is
      pinned by a test in `tests/test_wtclean.py`.
- [x] RED: `test_the_cli_never_targets_a_sibling_topics_cache_from_a_project_path` fails on the
      old script (the sibling cache is deleted), as do the bare-repo, separate-git-dir and
      missing `--cache-dir` tests. The home-directory and timeout tests were proven able to fail by
      deleting each guard in a scratch copy: both arms go red.
- [x] GREEN: every new sentence quoted back against the test that executes it.
- [x] Lost-result check: the refusal list, the exit codes and the dry-run-first rule are unchanged.
- [x] Description unchanged, so no routing keyword moved.
- [x] Security scan: all fixtures are tmp_path repos; no hosts, addresses or private paths added.
