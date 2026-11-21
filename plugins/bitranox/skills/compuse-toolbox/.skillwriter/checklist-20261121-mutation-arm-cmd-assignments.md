# checklist - mutation_arm --cmd takes leading NAME=value tokens as the arm's environment

One queued contribution: `--cmd 'CARGO_TARGET_DIR=/x cargo test -p crate'` was refused with
"--cmd CARGO_TARGET_DIR=/x: no such program". The script now takes leading `NAME=value` tokens as
the environment of the baseline and every arm; the `mutation_arm` row says so.

Decisions: none - the row documents script behaviour, whose decision is in mutation_arm.py's docstring Decisions block

## RED

- [x] Script: four new tests failed on the unfixed code with the reported refusal ("--cmd
      MUTARM_PROBE=on: no such program"), the helper stubbed so they failed on behaviour.
- [x] Text: quote-back (opus) on the pre-edit row said nothing about a leading assignment and
      inferred the arm would be INCONCLUSIVE (it was refused before mutating).

## GREEN

- [x] 160 passed, 1 skipped in tests/test_mutation_arm.py plus tests/test_mutation_check.py.
- [x] mutation_arm against its own fix: dropping the env merge KILLED both e2e tests on the owed
      assertion ("CHECK zero-case FAILED" not in "MUTARM_PROBE not set"); not stripping the
      assignments KILLED them too.
- [x] CLI run by hand: `--cmd 'PROBE=on python3 chk.py'` reached the child (KILLED by the
      mutation, output "PROBE on"); `--cmd 'PROBE=on'` refused, exit 2, "no program after the
      variable assignments", source untouched.
- [x] Quote-back (opus medium, haiku) on the new row: both quoted the new sentence.

## REFACTOR

- [x] Gap closed: whether the variables add to or replace the environment ("added to the
      inherited environment"). Declined: quoting a value with spaces (the row says the command is
      split without a shell, shlex on POSIX); a token that is not a valid name (it starts the
      program, pinned by test_a_token_that_is_not_a_shell_assignment_starts_the_program).
- [x] Row width unchanged (padding taken from the same cell), added text ASCII.
