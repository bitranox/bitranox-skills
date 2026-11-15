# checklist - a leak check after a refused call holds the exception while it counts

`references/silent-test-defeaters.md`, "Leaked and held resources", gains an entry: a test that
counts descriptors (or any resource) after a call that raises binds the `pytest.raises` result
and keeps it referenced past the count, because releasing the exception frees the frames that
hold the leaked object and refcounting closes it. SKILL.md is unchanged: its routing sentence
already sends "asserts that no file descriptor leaked" to this file, and the file's own intro
lists "asserts a descriptor was closed".

Decisions: d-20261115-175d0a45

## RED

- [x] Skill decisions read first: no rejected or removed entries for this skill.
- [x] Mechanism measured before writing it down: a function that opens a file and raises without
      closing it. With a bare `with pytest.raises(ValueError):` and a `/proc/self/fd` count after
      the block, the test PASSED on the leaking code; with `as refused` and `assert
      refused.traceback` after the count, it FAILED (`assert 13 == 12`).
- [x] Coverage check on the pre-edit reference file (inert quote-back probe, opus): "How must the
      exception be held, and why?" answered NONE; the probe's gap list said the descriptor entry
      does not mention traceback frames keeping descriptors alive.

## GREEN

- [x] Same question on the edited file, opus and haiku: both quoted the new entry verbatim
      ("Bind it and keep it referenced past the count", and the frames sentence) and described
      binding, counting, then referencing `refused.traceback`, plus the RED by deleting the close.
- [x] The code block in the entry is the measured probe's shape (names generalised).

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; recorded and decided.
- [x] Declined: "which exception type to bind" - the type the code under test raises; the
      example's `ValueError` is a placeholder, as everywhere in the file.
- [x] Declined: "how the count is taken" - the entry directly above covers it (specific
      descriptor, or the full `/proc/self/fd` set).
- [x] Width, fence and non-ASCII check over the added lines printed nothing; the entry after the
      insertion point ("A plain `mmap` keeps a descriptor") is self-contained; "RED it as above"
      binds to the entry directly above, which states the delete-the-close RED.
- [x] Decision recorded with `skill_decisions.py add` (rule entry with an anchor).
