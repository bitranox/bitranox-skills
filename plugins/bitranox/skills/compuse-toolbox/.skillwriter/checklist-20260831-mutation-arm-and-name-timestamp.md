# skill-writer checklist - compuse-toolbox (2026-08-31, mutation_arm + newest --name-timestamp)

Change: a new jig `mutation_arm.py` (mutate by exact anchor, run one test arm, report the failing
assertion, restore from a copy taken first), `--name-timestamp` on `newest.py`, and two repairs to
the index table itself.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] SCOPE RE-CHECKED BEFORE BUILDING, and it moved. The queued request was a whole mutation
      battery; `anchor_edit.py` had since shipped and already covers replace-at-exact-anchor-or-
      refuse AND copy-to-.bak-first, and `tests/mutation_check.py` covers batteries for ONE tool
      (its TOOL constant is srccount). What was genuinely missing is what the new jig does: RUN the
      named arm, report the failing ASSERTION, and mutate several anchors together. Delivering the
      original request would have rebuilt shipped code.
- [x] RED: 9 tests written first and watched fail. Three initially failed on an undefined harness
      constant rather than the behaviour owed - repointed to the module's real `TOOL`, and re-run
      until every arm failed on its own assertion, because a RED that failed on the harness was
      never watched failing on the behaviour.
- [x] The verdict is read from pytest's SHORT TEST SUMMARY, never a grep of the log. A test pins
      the motivating case: a traceback containing `with pytest.raises(KernelError):` alongside a
      summary line saying `DID NOT RAISE` must report DID NOT RAISE.
- [x] pytest exit 5 (nothing collected) maps to INCONCLUSIVE, not to "survived". Folding it into a
      pass would report an arm that never ran as a covered one - the false all-clear the jig exists
      to prevent. A test pins it.
- [x] Restore is verified byte-for-byte and runs in a `finally`; a failed restore is reported and
      forces exit 2, because it is the one outcome worse than a wrong verdict. Copies are index-
      prefixed so two mutations on one file, or two files sharing a basename, cannot restore the
      wrong bytes.
- [x] `newest --name-timestamp`: the warning condition is that the two keys pick DIFFERENT files,
      which needs no threshold. "The mtimes are much later than the stamps" would need a cutoff
      nobody can justify, and a wholly rewritten set can still have the same answer.
- [x] `--name-timestamp` REFUSES when nothing carries a stamp rather than falling back to mtime: a
      silent fallback answers the question the caller just said was the wrong one. A test pins it.
- [x] A stamp must parse as a real date - `build-20261345.log` is the right WIDTH and not a date,
      and reading it as one would be a fresh way to get the same silent wrong answer.
- [x] Index rows: both new capabilities are registered with the user's NOUN ("does this test
      actually assert anything?", "which backup is the latest?"), and the usage cells carry real
      runnable values, because a jig nobody finds gets hand-rolled again.
- [x] Two PRE-EXISTING defects in this table repaired, both verified present at HEAD before the
      change: an unescaped `|` inside a code span in the `adjudicate` row (GFM splits the cell and
      drops the surplus), and the `anchor_edit` row having NO usage cell at all - so the shipped
      table never told a reader how to run it.
- [x] Tests: 24 pass for newest, 9 for mutation_arm, and the new jig's tests drive REAL pytest
      against a real fixture project rather than a stubbed runner - what pytest actually reports is
      the entire value of the tool.
- [x] Scope: shared - generic RED/GREEN and file-selection mechanics, nothing project-specific.
- [x] Security scan: no hosts, addresses, credentials or private paths; fixtures are tmp_path.
- [x] CSO description: unchanged. "could a RED baseline ever fail" and "the latest backup or log,
      not ls sort tail" are already triggers covering both additions.
