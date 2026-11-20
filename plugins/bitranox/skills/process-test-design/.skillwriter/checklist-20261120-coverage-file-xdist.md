# checklist - a conftest COVERAGE_FILE under pytest-xdist

One queued contribution: the "A conftest cannot choose where pytest-cov writes its data"
paragraph in references/silent-test-defeaters.md said a conftest setting redirects nothing; it
now says that holds for the serial run only, and that under pytest-xdist the workers inherit the
variable, so their data lands elsewhere and the report says "No data to report".

Decisions: d-20261120-f4a4065f

## RED

- [x] Skill decisions read first: none rejected or removed for this paragraph.
- [x] Text check of the pre-edit file: the paragraph claimed the conftest "redirects nothing",
      with no xdist case.
- [x] Measured here before writing (covprobe): a conftest setting COVERAGE_FILE; the serial run
      wrote `.coverage`; the xdist run (2 workers, two `redir/.cov-conftest.*` files) reported
      "No data to report" with both tests passing.

## GREEN

- [x] Quote-back probe (opus, haiku): D1 answered with the new sentences; no NONE.

## REFACTOR

- [x] Declined (haiku): pinning pytest-cov and xdist versions in the prose - the measurement is
      recorded in the ledger entry.
- [x] Width, fence and ASCII checks on the added lines clean.
