# skill-writer checklist - compuse-toolbox (2026-11-15, ci_wait --ref resolves in a --repo directory)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`); Step 0b `show` run: no
      rejected or removed decision covers where `--ref` resolves.
- [x] Skill type: reference. The change rewords two sentences that state where `ci_wait --ref`
      resolves: the `ci_wait` row of the jig table and step (1) of the `no-runs` bullet. The
      script now resolves `--ref` in a `--repo` directory (`scripts/ci_wait.py`,
      `_target_sha` passes `_local_repo_dir(args.repo)` to `resolve_ref(cwd=...)`).
- [x] Code claim executed, not read: `tests/test_ci_wait.py::TestRefOnTheCommandLine::
      test_a_ref_is_resolved_inside_a_directory_repo_not_the_cwd` builds a real linked worktree
      with a commit the cwd lacks; it failed on the pre-fix script (polled the cwd's HEAD) and
      passes after. `test_a_ref_with_an_owner_name_repo_still_resolves_in_the_cwd` pins the
      OWNER/NAME case.
- [x] RED (pre-edit text pasted, opus and haiku `baseline-probe`): scenario cwd = main checkout
      (HEAD M), `--ref HEAD --repo <linked worktree>` (HEAD W). Both answered M, quoting
      "`--ref` resolves in the current directory's repo" - the text described the old behaviour.
- [x] GREEN (new text pasted, opus and haiku): both answered W, quoting "in the `--repo`
      directory when one is given (a linked worktree's HEAD is not the main checkout's)".
- [x] GREEN gap closed: both tiers had to infer the `--repo OWNER/NAME` case. Added "else (no
      `--repo`, or an `OWNER/NAME` one) in the current repo". Re-probe on the final text, opus and
      haiku: both answered W for the directory and M for OWNER/NAME, each quoting the governing
      words. Tiers: opus, haiku; cells: RED 2, GREEN 2, re-probe 2.
- [x] Gaps declined (pre-existing behaviour this change does not touch):
      - how a directory is told from OWNER/NAME: the script tests `os.path.isdir` first
        (`scripts/ci_wait.py` `_local_repo_dir`), and the row already says `--repo` takes either;
      - whether an OWNER/NAME `--repo` is cross-checked against the cwd's repository: it is not
        (`_local_repo_dir` returns None and nothing compares them); the user has not ruled on
        adding such a check, so the text stays silent;
      - whether the sha is on the remote, how a directory maps to OWNER/NAME, when the resolved
        sha is printed: already stated elsewhere in the row (no-runs hint, `--repo` resolved
        once, "prints the sha it resolved to") or outside this change.
- [x] GREEN against RED, both directions: no baseline answer lost; the RED arms' advice to
      compare the printed sha with the intended one is still supported by "prints the sha it
      resolved to".
- [x] Width and fence check over the added lines printed nothing; the paragraph after each edit
      was read (step (2) of the bullet still binds to "that repo"); table re-run through
      `reformat_tables.py`, which re-padded the column the longer cell widened.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-2f4b0cfe
