# Review checklist: retire a skill-covered pointer when both checks pass (2026-10-30)

Change: `references/dream-passes.md` "Point a rule at its skill or HOOK" now retires (archives,
never deletes) a covered rule's pointer when BOTH checks pass - (a) the rule quoted from the
INSTALLED plugin, covering the whole fact, and (b) why the trigger cannot fire without that skill
loaded (a step of the skill's own procedure creates the situation; sharing the topic is not
enough). Retirement follows the dream mode: `auto` archives via
`reconcile_memory_index.py --archive`, `propose` and any other mode only lists a proposed
retirement. Pinned facts and hook-only coverage are never retired. The Removal policy gains route
(4); SKILL.md step 11's report list names retirements with their (a) quote and (b) reason.
`docs/concepts.md` section 7 and the removal comment in `hooks/self_improve_signals.py` name the
new route.

## Type and test approach

- [x] Skill type: technique (a dream pass a reader applies). Test: application scenarios with two
      candidate pointers, one that passes (b) and one that does not, on the pre-edit and the final
      text, plus quote-back questions.

## RED

- [x] Contract test written first and seen failing:
      `test_pointing_pass_retires_a_pointer_only_on_both_checks_and_by_the_dream_mode` and
      `test_removal_policy_lists_the_covered_pointer_retirement_route` in
      `hooks/tests/test_dream_skill_contracts.py`. First run: `2 failed, 11 passed`
      (`AssertionError: Removal policy does not name the retirement route`, and the old
      "The dream does not delete such a rule" still present in the section).
- [x] Behavioural RED (opus, `baseline-probe`, pre-edit section pasted, mode `auto`): pointer A
      (a Findings-table rule only the report skill's step reaches) and pointer B (a SIGPIPE rule
      ordinary pipelines reach). Result: both KEPT, body rewritten to a pointer, nothing archived.
      Governing quote it gave: "The dream does not delete such a rule - the always-on trigger is
      its value." Its own gap 2: "No exception for a trigger that is never needed ... I kept A."
- [x] Inherited-context check: `redcheck.py --scenario ... --answer ... --corpus-cascade <repo>`
      exited 1 (STRONG term overlap). Reading the named documents: a project-level memory index
      line states the reach test ("keep the pointer unless that skill is loaded whenever the rule
      fires"); the higher hits share only generic terms. Route taken: the evidence of record is the
      text check of the artifact (the contract test above); the behavioural RED still failed
      honestly, because the pasted pre-edit text forbids deletion outright.

## GREEN

- [x] GREEN opus (final-draft section pasted, new scenario: A = `--batch-size` for a script only
      the skill's step 3 runs, B = editing a JSON config file): A retired - `ref_map.py` then
      `reconcile_memory_index.py --archive bulk-import-batch-size /opt/tree`; B kept with a
      concise-pointer body. Quoted: "Retire it only when BOTH checks pass:" and "If you can, (b)
      fails." `propose`: A listed as a proposed retirement, nothing archived.
- [x] GREEN haiku, same prompt: same verdicts (A retired with both commands, B kept); quoted
      "In `propose` (the default) and any other mode, archive nothing: list it as a proposed
      retirement." Tiers: opus + haiku, 2 cells, both correct.
- [x] GREEN against RED, both directions: RED's body-to-pointer rewrite for the kept rule is still
      produced in GREEN (B); the coverage proof via the shipped-text rule is still applied (both
      arms quote `--exclude-dir=.skillwriter`). Nothing RED produced is missing.

## Skill gaps (every one closed or declined)

- [x] Closed: "Which cached version counts when several are cached" -> (a) now names the
      `installPath` in `~/.claude/plugins/installed_plugins.json`.
- [x] Closed: "No command for rewriting a body" (RED gap 4, GREEN gaps) -> the pass names
      `factedit.py apply --body-file`, home `<plugin>/skills/meta-dream-tree/`, as step 7 shows.
- [x] Closed: "Shrink A's body before archiving?" -> "archive the fact as it is (never delete it,
      and do not shrink its body first)".
- [x] Closed: "Body rewrite can drop content the skill lacks" -> "keeping in it any directive,
      number or caveat the skill does not state"; and (a) "The quote must cover the WHOLE fact".
- [x] Closed: "Grep target not given" -> "Run the search there."
- [x] Closed: "How to find every level" -> the `find <anchor> -name CLAUDE.local.md -exec grep -l
      'mem:<slug>)' {} +` line. Verified against a real store: it listed the one level holding a
      known slug.
- [x] Declined (covered elsewhere): whether a body rewrite waits in `propose` -
      `references/dream-core.md` Mode: "**`propose`** (default): apply safe private-memory
      consolidation".
- [x] Declined (covered elsewhere): `<anchor>`, `<level>`, `<plugin>` placeholders and the
      ref_map/fold bullet the excerpt omitted - defined in SKILL.md and in the full section (the
      last fold bullet, the Removal section's script home).
- [x] Declined (pre-existing, owned elsewhere): "the pass names only bitranox skills" - the
      scenario's fictional `acme:` prefix tripped it; the pass is about this marketplace's skills.
- [x] Declined (judgement the pass leaves open): borderline (b) triggers and multiple
      `installed_plugins.json` scopes - the (b) test is a judgement by design; a plugin installed
      at two scopes is rare and either `installPath` is a loaded version.
- [x] Declined (covered elsewhere): reporting a pinned fact - dream-core.md Boundaries owns it.

## Quote-back on the final text (opus, effort medium)

- [x] Round 1, 8 questions (installed version, body command, shrink first, pinned, `--force`,
      hook-only, `propose`, partial coverage): all 8 answered with a direct quote of the governing
      sentence, none NONE.
- [x] Round 2 after the last fixes, the 4 touched questions (uncovered retry line, grep location,
      every level, JSON trigger): all 4 quoted correctly, e.g. Q3 "Find those levels with
      `find <anchor> -name CLAUDE.local.md -exec grep -l 'mem:<slug>)' {} +`, never an
      ancestor-chain read". Its gaps were placeholders defined outside the excerpt and a reading
      of the opening "instead of restating content" vs the keep-uncovered-content clause (no
      conflict: content the skill lacks is not restating it). No new undecided gap.

## Mechanism claims checked against the code

- [x] `reconcile_memory_index.py --archive` drops the pointer and moves the body to `.archive/`
      only when no other level points at the slug (`archive_entry`, "archive the body ONLY when no
      other level in the tree still points at this slug"), and refuses the last pointer while a
      fact or a level's CLAUDE.md names it (`ArchiveBlocked`), `--force` overriding.
- [x] Pinned facts: dream-core.md Boundaries, "treat it as un-archivable by the dream's own policy
      anyway: report it".
- [x] `factedit.py apply --help` lists `--body-file`.
- [x] `installed_plugins.json` entries carry `installPath` and `version`.

## Quality checks

- [x] No version-history phrasing: the finder pattern over the added lines returned 0 hits.
- [x] ASCII only: `git diff | grep '^+' | grep -cP '[^\x00-\x7F]'` printed 0.
- [x] No private hosts, users or paths; example paths are `/opt/tree` and placeholders.
- [x] Consistency sweep: `grep -rn` over the dream family, meta-self-improve, hooks and docs for
      the old "does not delete such a rule", "three routes" and the removal list found
      dream-passes.md (Removal + pass), `hooks/self_improve_signals.py` and `docs/concepts.md`
      section 7; all three updated. meta-dream-nap defers behavioural passes and states no
      never-delete rule.
- [x] Tests: `hooks/tests/` plus `meta-dream-tree/tests/` with CI's dependency set:
      `8476 passed, 7 skipped, 1 xfailed`.
