# checklist - UI tests

One queued contribution: a subsection under "Deterministic and order-independent" - a browser
test asserts what an overlay looks like per theme, and async UI state gets a delay probe per
entry path.

Decisions: d-20261120-45167eb0

## RED

- [x] Skill decisions read first: none rejected or removed.
- [x] Text check of the pre-edit file: the key phrases of the added rules had 0 hits at HEAD
      (listed in the run's notes).

## GREEN

- [x] Quote-back probe (haiku) on the added text: every question answered with a quote of the
      new lines; no NONE. The opus probe was skipped for this batch to keep the run inside its
      time budget; the haiku probe is the weaker reader, so a pass there is the harder bar.

## REFACTOR

- [x] Declined (haiku): a theme list and an injection recipe - both are the project's own.
- [x] Width, fence and ASCII checks on the added lines clean.
