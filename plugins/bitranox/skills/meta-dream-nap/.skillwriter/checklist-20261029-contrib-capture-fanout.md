# skill-writer checklist - meta-dream-nap (capture fan-out rules)

- [x] Change: step 1 fan-out brief rule (c) - a pinned target is reported via `apply --dry-run`,
      never `--allow-pinned`; `show --body > f` round trip; `session-review --prose` for a long
      owed stretch; a capture below the chain widens the backup (`--from <descendant>`) and
      `reconcile --check` to that level and is named in the report.
- [x] RED (text): `git show HEAD:<SKILL.md> | grep -c` gave 0 for "allow-pinned", "--prose",
      "BELOW the chain".
- [x] GREEN (quote-back, 1 each): "(c) A PINNED target is never written"; "read it with
      `dream_state.py session-review --prose`"; "**A capture that wrote BELOW the chain** ... take
      the backup with `--from <that descendant>` (its chain holds the cwd's chain)".
- [x] Claim probed: a fixture top/proj/sub with one fact per level, `store_manifest.py backup
      --from top/proj/sub --scope chain` recorded all three levels (reference-a-top,
      reference-b-proj, reference-c-sub), so a descendant-rooted chain backup covers the cwd chain.
- [x] Claim probed: `apply --dry-run` on a pinned fact needs no opt-in
      (tests/test_factedit_round_trip.py::test_a_dry_run_of_a_pinned_fact_needs_no_opt_in...).
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
