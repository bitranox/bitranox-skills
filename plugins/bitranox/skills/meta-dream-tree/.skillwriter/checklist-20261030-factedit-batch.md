# skill-writer checklist - meta-dream-tree (factedit apply --batch)

- [x] Change: `factedit.py apply --batch <file.jsonl>` rewrites several facts in one call. SKILL.md
      (the `factedit.py` tool entry) names it as the route for a change spanning several facts,
      with its line keys, relative-path rule, the whole-batch pre-check, the stop-at-first-failure
      report and the re-run. `references/dream-passes.md` (archiving a folded fact) sends a
      re-point hit inside a store fact through `apply --slug` or, for several, `apply --batch`,
      never a script writing `facts/*.md`.
- [x] Code TDD: `tests/test_factedit_batch.py` (20 tests) failed first, all 20 with
      `factedit.py apply: error: the following arguments are required: --slug`, then passed.
      Mutations: dropping the per-entry pre-check turned 5 RED, dropping the stop-at-failure
      `break` turned 2 RED; restored file byte-compared (`cmp`) before the rerun went green.
- [x] Every mechanism claim in the new text checked against the code and a test:
      pre-check list (unknown or duplicate slug, unreadable file, over-cap hook, pinned without
      `--allow-pinned`): `_preflight` / `parse_batch` in factedit.py, tests
      `test_every_problem_is_listed_and_nothing_is_written`,
      `test_an_over_cap_hook_in_one_entry_refuses_the_whole_batch`,
      `test_a_pinned_entry_without_allow_pinned_refuses_the_whole_batch`; relative paths from the
      batch file's dir: `_batch_path`, `test_relative_paths_in_an_entry_resolve_against_the_batch_files_dir`;
      `--dry-run` / `--allow-pinned` over the whole batch:
      `test_a_batch_dry_run_stages_every_entry_and_invokes_nothing`,
      `test_allow_pinned_routes_the_pinned_entry_through_amend_pinned`; stop and report:
      `test_a_failure_mid_way_stops_and_reports_applied_failed_and_not_applied`; real engine:
      `test_a_batch_through_the_real_engine_rewrites_every_body`.
- [x] Corpus check: `redcheck.py --corpus-cascade <worktree>` reported STRONG term overlap with
      facts on archiving and fact bodies; none names a multi-fact write route (the verb is new),
      so the RED below could fail and did. Recorded: the text check (pre-edit text holds no
      `--batch`: `git show HEAD:<path> | grep -c -- --batch` printed 0 for SKILL.md and
      dream-passes.md) is the primary evidence; the behavioural arms are supporting.
- [x] RED (pre-edit excerpts from `git show HEAD`, text-only probe agent, opus and haiku, 2 cells):
      asked for a single command rewriting several facts, both answered NONE; opus wrote a
      Python driver looping `factedit.py apply` per slug, haiku a bash loop, both continuing past
      a failure and neither checking the other entries before writing.
- [x] GREEN (edited excerpts pasted, same scenario, opus and haiku, 2 cells): both quoted
      "A change spanning several facts, such as a re-point across N facts, goes through ONE
      `apply --batch <file.jsonl>`", wrote one JSONL batch, and quoted "checks every entry before
      writing any" for the unknown-slug case and "stops at the first failure, naming the slugs
      applied, the one that failed, and those not applied" for a mid-way refusal.
- [x] Skill gaps from GREEN, closed: relative-path base (added "relative paths resolve from the
      batch file's dir"); whether a pinned entry is caught before writing and whether `--dry-run`
      / `--allow-pinned` reach the batch (added the pre-check list and "`--dry-run` and
      `--allow-pinned` cover the whole batch"); what to run after a mid-way failure (added "fix
      the failed entry, then re-run a batch of it plus the not-applied ones").
- [x] Skill gaps declined, with reasons: the `<plugin>` path and launch shim (covered: SKILL.md
      line 76 points at references/dream-core.md "Script homes"); what text replaces a `[[slug]]`
      link (owned by the fold procedure, unchanged by this edit, reported by RED too); whether
      `--dry-run` writes nothing (covered in the same paragraph: "`--dry-run` stages and prints
      the change without it"); the unmatched ")" a probe saw (its excerpt began mid-parenthetical;
      the parenthetical opens at "`factedit.py` (reword"); whether re-applying an applied entry is
      harmless (the text tells the reader to re-run only the failed and not-applied ones).
- [x] Re-probe on the final text (opus at effort medium and haiku, 2 cells, quote-back): both
      quoted "relative paths resolve from the batch file's dir", the pre-check sentence for the
      pinned case, and "fix the failed entry, then re-run a batch of it plus the not-applied
      ones". Their one new gap (a subagent holding a pinned fact in a batch) is closed in the
      meta-dream-nap skill, whose rule (c) governs subagents; see its checklist of this date.
- [x] RED vs GREEN diffed both ways: no RED result lost; both GREEN arms kept the pinned-fact
      `--dry-run` hand-back RED had, and the separate grep sweep of other docs.
- [x] Width and fence check over the added lines printed nothing for SKILL.md and
      dream-passes.md; the paragraph after each insertion read: "The PreToolUse nudge names
      `statusrot.py` and `factedit.py`" still binds to the tool list, and the dream-passes
      addition sits after the grep-sweep sentences so "For many slugs" still binds to the sweep.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only (`grep -nP '[^\x00-\x7F]'` printed nothing), present tense, the history-phrase
      finder found nothing in the added lines.
- [x] Security scan: no secrets, hostnames, private paths or PII in the added lines.
- [x] Tests: `meta-dream-tree/tests` plus `hooks/tests/test_store_edit_guard.py` with the CI
      dependency set: 568 passed; `hooks/tests`: 7987 passed, 7 skipped, 1 xfailed.
