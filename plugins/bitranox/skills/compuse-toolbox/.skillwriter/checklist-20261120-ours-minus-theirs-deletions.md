# checklist - conflict_resolve rule ours-minus-theirs-deletions

One queued contribution: a conflict_resolve rule for the diff3 hunk where upstream deleted a line
next to one our side added. The jig gains `ours-minus-theirs-deletions`: ours with every base line
theirs deleted removed. It refuses when theirs added, rewrote or moved a line (moving is refused
on purpose: keeping ours' order would undo the move), when there is no base section, when ours
does not keep a deleted line verbatim, and when ours holds more copies of a deleted line than base.
The tool table row names the rule and its refusals.

Decisions: none - additive rule; the moved-line refusal is recorded in the module docstring

## RED

- [x] Skill decisions read first (`show compuse-toolbox --kind rejected,removed`): nothing on conflict_resolve.
- [x] Text check at HEAD: `ours-minus-theirs-deletions` had 0 hits in SKILL.md and the script.
- [x] New tests fail on the old script: mutation_arm KILLED both mutated guards (the pure-deletion
      check and the copy-count check).

## GREEN

- [x] 86 tests pass in tests/test_conflict_resolve.py.
- [x] Quote-back probe (haiku) on the row and the docstring paragraph: all four questions answered
      by quotes (rule choice, moved line refused, no base refused, nothing written on refusal).

## REFACTOR

- [x] Table re-padded by the formatter; ASCII and width checks on the added text clean.
