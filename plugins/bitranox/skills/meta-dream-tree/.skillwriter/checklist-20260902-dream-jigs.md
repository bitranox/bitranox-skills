# skill-writer checklist - meta-dream-tree (2026-09-02, backup/manifest and dedup jigs)

Change: two scripts ship with the skill - `store_manifest.py` (backup + order-independent manifest,
`--scope tree|chain`, and the `verify` that diffs it back) and `dedup_scan.py` (near-duplicate
CANDIDATES with a planted control and a printed score distribution). Steps 2, 4 and 8 now call them
instead of describing the work.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] RED route: COVERAGE CHECK AGAINST THE FILE, not a behavioural probe. Both steps already told
      a reader WHAT to do; the defect is that each run re-implemented it, so there is no wrong
      answer for an agent to give and a pressure scenario has nothing to fail on. Pre-change, a
      grep for `store_manifest` and `dedup_scan` over the skill returned 0 hits, and no script
      shipped for either step.
- [x] Each step names the script's HOME and launch shim at the point of use
      (`<plugin>/skills/meta-dream-tree/`, via `hooks/run-python.sh`), so the reference resolves
      for a reader whose context does not already hold this skill's base directory.
- [x] The two enumeration traps are stated where the walk is prescribed, because they are what
      every re-implementation got wrong: a gitignore-aware `grep -r` SKIPS the pointer files, and
      an exact-match prune of `.venv` misses `.venv-win` and `venv-<user>`, so vendored copies
      read as levels.
- [x] Step 4 tells the reader to READ THE CONTROL LINE FIRST and says what its absence means - a
      scorer that cannot fire and a clean tree both report zero candidates, so the empty list is
      only worth anything while the control fired.
- [x] The output is framed as CANDIDATES requiring both bodies to be read, never as duplicates.
- [x] Step 8's verify states which difference is legitimate (`level`, reported as `moved`) and
      that anything else is a loss to explain, so the diff is a contract rather than a formality.
- [x] Both scripts ship tests that pass: `store_manifest` 16, `dedup_scan` 16.
- [x] Both verified against the real store, not only fixtures: the manifest backed up and verified
      993 pointers as IDENTICAL, and the scanner scored 448,872 pairs with its control firing.
- [x] Two defects found by those runs are fixed and pinned by regression tests: a backup written
      under the anchor put COPIES of every level file inside the scope, so `verify` reported the
      whole tree as moved; and the planted control scored exactly 1.00 because it only REORDERED
      words, which a word-set scorer reads as an identical input - it now drops and adds words, so
      it is a genuine near-duplicate.
- [x] Scope: shared. Both describe the dream's own contract, not one store's contents.
- [x] Security scan: no hostname, username, absolute local path or address in either script or its
      tests.
- [x] CSO description: unchanged and still accurate at 480 characters - the two scripts are steps
      inside an existing procedure, not new triggering situations.
- [x] Token budget: the body gained two short call sites; the detail lives in each script's
      `--help` and docstring.
