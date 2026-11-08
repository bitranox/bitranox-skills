# skill-writer checklist - compuse-toolbox (2026-11-06, git_state foreign upstream and --fetch)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The change is the `git_state` row of the jig table: its description
      names `--fetch` and the foreign-upstream judgement, its invocation column gains `[--fetch]`.
- [x] Behavioural RED not used: the lesson is in this machine's always-loaded memory and the
      skill is installed, so a probe would inherit or load it. Route: text check of the file.
- [x] RED, text check of the pre-edit row (`git show HEAD:<path>`): 0 hits for `--fetch`.
      New row: 1.
- [x] The row's claims match the code and were executed: `git_state.py --fetch` runs
      `git fetch --prune` first (`tests/test_git_state.py::test_fetch_refreshes_the_counts`), and
      a foreign upstream is judged against `origin/<branch>`
      (`test_a_foreign_upstream_whose_namesake_equals_head_is_in_sync_but_flagged`); a live run on
      a worktree whose branch tracks `origin/master` flagged it.
- [x] GREEN: the row was part of the text shown to the opus and haiku probes recorded in
      `compuse-git/.skillwriter/checklist-20261106-foreign-upstream.md`; both picked `--fetch` for
      "counts as of now" and quoted it.
- [x] Skill gaps: none specific to this row; the shared ones are decided in the compuse-git
      checklist.
- [x] Table re-run through `reformat_tables.py`; the column already had room, so only the row
      changed.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: none - the text describes what the code does; the choices it rests on are in the
      `Decisions:` blocks of `hooks/git-footgun-guard.py` and `compuse-toolbox/scripts/git_state.py`.
