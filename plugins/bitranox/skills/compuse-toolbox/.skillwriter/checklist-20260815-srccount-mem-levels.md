# compuse-toolbox - two tools added: srccount, mem_levels

`srccount` is contributed from a local personal toolbox where it had been hardened in use.
`mem_levels` is new, written TDD for this change.

## RED

- [x] `srccount` retrieval RED, run against the index WITHOUT its row, inert probe agent (no shell,
      no filesystem), NONE stated as an acceptable answer. The agent answered **NONE**, hand-rolled
      `find <dirs> -type d \( -name '.venv' -o -name 'venv' ... \) -prune -o -type f ... | wc -l`,
      and named the failure itself: "needs the folder names guessed correctly or it silently
      inflates the count - the exact failure mode the user is worried about". The gap is real.
- [x] `mem_levels` RED, code arm: the module did not exist, all 11 tests failed at import.
- [x] `mem_levels` RED, evidence arm: the chore is documented as re-derived by hand, and the
      hand-rolled `[a-z0-9-]+` slug regex produced a phantom dangling body against a store the
      shipped `--check-tree` had correctly reported clean. `test_a_dotted_slug_is_found` is that
      exact case, first in the file.

## GREEN

- [x] `srccount`: 62 tests pass in the marketplace layout.
- [x] `mem_levels`: 11 tests pass.
- [x] `srccount` retrieval GREEN, same probe and question with the row present: picked `srccount`,
      quoted the row's reasoning back, and stated it would NOT hand-roll a `find | wc -l`.
- [x] `mem_levels` retrieval GREEN: picked `mem_levels`, produced the exact correct invocation
      including `--root` at the tree anchor, and recognised unprompted that the slug in the question
      contains a dot - the case the tool exists for.

## Cross-validation against a shipped instrument

- [x] `mem_levels` run against a real 88-level tree agrees with `reconcile_memory_index.py
      --check-tree` exactly: same level count, no duplicates, no dangling bodies.
- [x] Known-positive control: with an orphan body planted, BOTH tools report it; with it removed,
      neither does. The agreement is a measurement, not two tools sharing one blind spot.

## Skill gaps reported by the GREEN runs

- Declined (probe artifact, not a skill defect): both agents said the tool's own CLI syntax was
  missing. The probe prompt pasted only the "Use it when" column; the real table carries an Invoke
  column with a runnable example for every row, which is what a reader sees.
- Closed: the `srccount` row initially omitted `--audit` and the content-marker behaviour
  (`pyvenv.cfg` / `CACHEDIR.TAG` evidence over name matching). Both are non-obvious capabilities a
  reader cannot guess, so the row now carries them.
- Declined (owned by `--help`, per this skill's standing rule that per-tool arguments live there):
  the default extension set's membership, and the plain-text output format.
- Declined (unanswerable from any index): both agents noted the task did not name the target paths.
  That is the asking user's input, not a property of the table.

## Quality checks

- [x] Contributed copy scrubbed of private specifics: the one machine-tree example in the docstring
      and one tree name in a test docstring were replaced with generic values. Sweep for
      `rnprivat|rotek|provmm|softdev|bitranox-systems|srvadmin|/home/|/media/` over both shipped
      files returns nothing, with a control confirming the sweep still matches text that is present.
- [x] Both scripts are import-safe (work behind `main()`, run under `if __name__ == "__main__":`)
      and stdlib-only, so they import in a bare environment with only pytest.
- [x] Both ship tests covering every main function, not import smoke tests.
- [x] `mem_levels` follows the CLI contract: `--json` envelope, JSON still emitted on failure,
      diagnostics on stderr, format-independent exit codes (0 found / 1 not found / 2 error).
- [x] Read-only by construction: `mem_levels` never writes to the store; writes go through the
      engine.
- [x] Frontmatter description UNCHANGED - no trigger-map rebuild required.
- [x] ASCII only; no secrets, credentials, private hostnames or IPs in the diff.
