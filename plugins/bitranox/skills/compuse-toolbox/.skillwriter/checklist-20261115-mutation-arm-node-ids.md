# skill-writer checklist - compuse-toolbox (2026-11-15, mutation_arm: one node id per --test)

- [x] Receipt issued; Step 0b `show` run: no rejected or removed decision covers mutation_arm's
      `--test`, its log dir or battery node ids.
- [x] Premise checked against the script: `--test` took a single value, so `"tests/a.py
      tests/b.py"` or `"tests -q -x"` reached pytest as one path, the baseline exited 4 (usage
      error) and the tool reported a RED baseline; `--log-dir` reused fixed names, so a second
      run overwrote the first run's logs; a battery naming a whole module with slow tests ran
      past the command limit.
- [x] Code: `scripts/mutation_arm.py` refuses an empty id, a leading option, or a value of
      several space-separated paths or pytest options (exit 2, before anything is written);
      `--test` repeats; pytest exits 4 and 5 are named in the reason and the baseline message
      ("the baseline did not run ... - this is not a red baseline"); `--log-dir` claims the
      first free `-N` suffix with an exclusive create and prints `log: <path>`.
- [x] RED for the code: 17 new tests in `tests/test_mutation_arm.py` failed on the pre-fix
      script and pass after; the repeated `--test` test uses two mutations so the arm must run
      both files to be KILLED.
- [x] RED for the text: the pre-edit reference said "`--test` takes a single node id", and the
      row said nothing of exits 4/5 or log names (text check).
- [x] GREEN (opus and haiku quote-back): both answered `--test a --test b`, refusal of the
      string, "reported as that, never as a red baseline", "never overwrites", and "list the fast
      node ids", each quoting the new text. Both asked which exit code the refusal and an exit
      4/5 baseline get - closed with "(exit 2)" and "(exit 2, the arm never ran)", checked in
      `_refuse` and `exit_code_for` and pinned by the existing exit-2 tests.
- [x] Gaps declined: the battery-arm naming across separate runs relies on the same suffix rule,
      which "never overwrites" already states.
- [x] Width and fence check over the added lines printed nothing (the one flag, a code span
      wrapped across two lines in the reference, is pre-existing); table re-run through
      `reformat_tables.py`.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-701c044b
