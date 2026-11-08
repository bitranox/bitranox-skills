# skill-writer checklist - meta-dream-nap (2026-11-08, named commands and a chain-scoped dedup)

Step 1 now says the `show --body` file carries the frontmatter frame and goes back unstripped,
and that an owed earlier transcript is marked with `session-reviewed --prose --transcript PATH`.
Step 2 names `store_manifest.py backup --scope chain`; step 3 names `dedup_scan.py --scope chain`
(new: `dedup_scan.load_facts(scope="chain")` and `--scope`, tests in
`meta-dream-tree/tests/test_dedup_scan.py`); step 6 names `store_manifest.py verify --out` and
one `reconcile_memory_index.py --check` call over the whole chain, with its home.

Decisions: d-20261108-e85ee49b, d-20261108-d109a38a

- [x] Step 0b: the edit guard showed one rejected decision (d-20261106-57ee2fca: do not replace
      the reconcile step); this change keeps the step and names its real command, so nothing
      reverses it.
- [x] Mechanism claims checked: `store_manifest.py backup/verify --help`, `reconcile --help`
      (dirs narrow->broad for --check), `dream_state.py --help` (`--transcript PATH` for both
      session-review verbs, "Pass the same PATH to both"); `factedit.py show --body` printed the
      frame (run on a real fact); `memory_engine._framed_body` passes a framed body through and
      `_synced_frame` re-syncs `description:`.
- [x] RED: the two new dedup_scan tests failed (TypeError: no `scope`; CLI exit 2) before the
      change; 162 dedup_scan + store_manifest tests pass after. Text check, pre-edit: step 2 and
      step 6 named no command; step 1 said `show --body` writes "the body alone".
- [x] Real run: `dedup_scan.py --from <marketplace repo> --scope chain` scanned 609 facts in 29 s,
      control detected, 0 candidates (the tree-wide default had been stopped after ~3 minutes).
- [x] GREEN, the four passages pasted, opus and haiku: frame round trip, owed transcript marking,
      backup/verify/reconcile commands, exit 1 and exit 2 handling, and a control (a full tree
      dream must NOT pass --scope chain). Both passed the control; haiku split reconcile into one
      call per level.
- [x] Gaps closed: reconcile is ONE call over the whole chain, anchor included; exit 2 puts chain
      dedup on the deferred list as not done. Re-run (haiku) on the final sentences: one call,
      and the not-done report. No new undecided gap.
- [x] Gaps declined: the write-back program (step 1's fan-out rule names `factedit.py apply`
      three lines above; the probe saw an excerpt); which slug survives a fold (a judgement per
      pair, already the dream's merge rule); retrying after exit 2 (deferred is the honest
      answer inside a nap's budget).
- [x] Width and fence check over the added lines printed nothing. ASCII only.
