# skill-writer checklist - meta-dream-nap (factedit apply --batch in the subagent rules)

- [x] Change: step 1's rules for fanned-out subagents. Rule (a) sends deltas to SEVERAL existing
      facts through one `factedit.py apply --batch <file.jsonl>` (line keys `slug`, `body_file`,
      `hook_file`, `type`, all but `slug` optional), which checks every entry before writing any.
      Rule (c) adds that a batch holding a pinned fact is refused whole, so the pinned one is left
      out and dry-run on its own. Two adjacent fixes in the same paragraph: "states two rules"
      now reads "three rules" (the paragraph lists (a), (b) and (c)), and rule (b) says "two
      subagents' work lists" instead of "two batches", which now collided with `--batch`.
- [x] Mechanism claims checked against code and tests in `meta-dream-tree/factedit.py`: the
      pre-check before any write (`cmd_apply_batch` runs `_preflight` over every entry and
      returns 2 before `_run_entry`; `test_every_problem_is_listed_and_nothing_is_written`); a
      pinned entry refuses the whole batch
      (`test_a_pinned_entry_without_allow_pinned_refuses_the_whole_batch`); the four line keys
      (`BATCH_KEYS`, plus `title` and `level`, which the subagent rules do not need;
      `test_an_entry_can_carry_hook_file_title_type_and_level`).
- [x] Corpus check: `redcheck.py --corpus-cascade <worktree>` overlap is on archiving and fact
      bodies; no document names a multi-fact write route (the verb is new). Text check: the
      pre-edit text holds no `--batch` (`git show HEAD:<path> | grep -c -- --batch` printed 0).
- [x] RED (pre-edit rule text from `git show HEAD`, beside two meta-dream-tree excerpts,
      text-only probe agent, opus and haiku, 2 cells): asked for one command rewriting several
      facts, both answered NONE; both built a per-slug loop around single `apply` that continues
      past a failure, opus as a Python driver script.
- [x] GREEN (edited text pasted, same scenario, opus and haiku, 2 cells): both wrote one JSONL
      batch and quoted "deltas to SEVERAL existing facts go through one `factedit.py apply
      --batch <file.jsonl>`" and "which checks every entry before writing any".
- [x] Gap from GREEN and the meta-dream-tree re-probe, closed here: a subagent with a pinned fact
      among several (added "A batch holding a pinned fact is refused whole, so leave it out of
      the batch and dry-run it on its own"). Re-probe on haiku: it batched the six unpinned facts,
      ran `apply --slug <slug5> ... --dry-run` for the pinned one, quoted that sentence, and
      answered NONE to writing with `--allow-pinned`.
- [x] Gap from that re-probe, closed here: whether `type` may go in a batch line (added it to the
      example, "all but `slug` optional"). Quote-back on haiku: it quoted that line and wrote
      `{"slug": ..., "body_file": ..., "type": "project"}` and a hook-only
      `{"slug": ..., "hook_file": ...}`; its remaining gap, the list of valid `type` values,
      predates this edit (the single form's `[--type <kind>]` names none either) and is declined:
      `factedit.py apply` refuses an unknown type and prints the engine's list (`plan_apply`,
      `test_an_unknown_type_in_an_entry_refuses_the_batch`).
- [x] Gaps declined, with reasons: `<plugin>` path, slugs and scratch location (placeholders the
      caller fills, unchanged by this edit); how a pin shows before `apply` (`factedit.py show`
      prints `pinned`, see `meta-dream-tree/factedit.py` `_render_fact`; owned by meta-dream-tree's
      tool text, not this rule list); the format of a dry-run delta (handed back verbatim, as the
      rule says).
- [x] RED vs GREEN diffed both ways: no RED result lost; the pinned `--dry-run` hand-back and the
      read-first `show` survive in every GREEN arm.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion ("`show --body --slug <slug> > f` writes the body alone") still reads on its own.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, history-phrase finder found nothing in the added lines.
- [x] Security scan: no secrets, hostnames, private paths or PII.
