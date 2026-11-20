# checklist - a quadratic regex start in a test file can be the input under test

One queued contribution. After "Prove a rewrite with both": in a test file, replay the test's own
inputs through the old and the proposed pattern before the fix, and keep the pattern with a
comment when what the test reads differs.

Decisions: d-20261120-6b5ea9f2

## RED

- [x] Skill decisions read first: none rejected.
- [x] Premise replayed: on the test's NESTED string, `(?m)^(\s*)def target\(` matches at offset 23
      with group 1 = newline plus four spaces; `(?m)^([^\S\n]*)def target\(` at 24 with four
      spaces. The test (compuse-toolbox tests/test_renamescope.py) already keeps the pattern with
      such a comment.
- [x] Text check at HEAD: "In a TEST file" 0 hits.

## GREEN

- [x] Quote-back probe (haiku): replay first, keep with a comment, and the copy-of-control outcome
      all answered by quotes.

## REFACTOR

- [x] Width and ASCII checks clean.
