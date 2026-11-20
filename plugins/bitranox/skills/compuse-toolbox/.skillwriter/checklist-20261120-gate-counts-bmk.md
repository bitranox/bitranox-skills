# checklist - a gate whose wrapper prints no counts

One queued contribution with two parts. The indented verdict line it asked to document was
already documented (the `gate` row's "exact stdout shapes" and gate.py's --help, since
2026-10-30). The other part is added to the `gate` row: a wrapper that prints no test counts,
such as bmk's `make test` in JSON mode, is judged on exit status alone, so a new test file is
shown to run with `pytest -q <file>`.

Decisions: d-20261120-930ff9dd

## RED

- [x] Skill decisions read first: three rejected entries (ledger for jigs, ci_wait verdict line, --name help), unrelated.
- [x] Text check of the pre-edit file: the key phrases of the added rules had 0 hits at HEAD
      (listed in the run's notes).

## GREEN

- [x] Quote-back probe (haiku) on the added text: every question answered with a quote of the
      new lines; no NONE. The opus probe was skipped for this batch to keep the run inside its
      time budget; the haiku probe is the weaker reader, so a pass there is the harder bar.

## REFACTOR

- [x] Table re-padded by the formatter after the edit.
- [x] Width and ASCII checks on the added text clean (a table cell).
