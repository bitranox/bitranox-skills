# Review checklist: process-test-design, queued contributions (2026-10-30)

Entries covered, one edit each:

1. Doctests in an extensionless script (`python3 -m doctest` reads it as text) - new bullet in the
   mechanics list ("Ten" became "Eleven"; the list now holds 11 bullets, counted with awk).
2. A test that replaces `PATH` with a stub dir must supply the ordinary commands - new paragraph
   after the stand-in-on-PATH paragraph.
3. Timed stand-ins against a real deadline: put each far from it - new bullet after the clock-read
   bullet under "Deterministic and order-independent".
4. A silent fake peer must still consume the request - new bullet under "Prefer real over mocked".
5. Adversarial table: "structurally empty" in the Structure row, plus a paragraph on every form of
   empty.

## Evidence

- [x] Claims verified against the real behaviour, not memory:
      - `python3 -m doctest mytool` on an extensionless file with a doctested function: rc 1,
        `NameError: name 'add' is not defined` (the file is parsed as text). The same file loaded
        with `SourceFileLoader` + `spec_from_loader` + `module_from_spec`, registered in
        `sys.modules`, then `doctest.testmod(module)`: `TestResults(failed=0, attempted=2)`.
        `importlib.util.spec_from_file_location('mytool', './mytool')` printed `None`.
      - The other four entries are test-design patterns with no tool behaviour to run; their
        mechanisms (buffer fill on an unread pty, `command not found` under a replaced PATH,
        margin loss near a deadline, `strip()` missing a frame-only input) are stated as shapes.
- [x] RED as a text check on the pre-edit file (`git show HEAD:<path>`): `SourceFileLoader|TEXT file`
      0 hits, `REPLACES .PATH|command not found` 0, `SILENT peer|STALLED link` 0,
      `structurally empty|form of empty` 0, `far from it|start delay` 1 hit (line 356, "the leak
      surfaces far from its cause", unrelated). After the edit: 2, 2, 2, 2, 3.
- [x] GREEN probe (`bitranox:baseline-probe`, haiku, the edited excerpts pasted as the skill under
      test, five scenario questions, quote-back required): every answer quoted the new governing
      sentence and took the intended action (Q1 "read it from the socket or pty on the fake's side
      and assert it arrived"; Q2 RED "not valid", link the tools or prepend; Q3 frame-only, comments
      only, empty envelope; Q4 0.05 s / 2.5 s plus the start-delay proof; Q5 the SourceFileLoader
      recipe with `attempted > 0`).
- [x] Skill gaps from the probe, each decided:
      - "Which child should be quick or slow" - declined: the test's own subject decides it.
      - "Table row and prose state the same idea" - declined: the row lists the input, the
        paragraph says why a fix must cover it; they do not differ.
      - "How long the fake must read / how to assert arrival on a pty" - declined: the read and
        the assertion depend on the protocol under test.
      - "Whether doctest examples see module globals" - declined: `testmod(module)` runs them in
        the module's namespace by definition.
- [x] Width and fence check over the added lines (the script in meta-skill-writer) printed
      nothing; the paragraph after each insertion point was read: no back-reference re-bound, no
      duplicated bullet.
- [x] ASCII only: `grep -nP '[^\x00-\x7F]'` printed nothing.
- [x] Front matter parses with `yaml.safe_load` (`['description', 'name']`); tables canonical
      (`reformat_tables.py` reports Unchanged).
- [x] No private paths, hosts or names; example path `/usr/local/sbin` is generic.

## Integration note

The minimal-PATH entry (coreutils in a replaced PATH) shipped first in a parallel release (10.8.1)
with a fuller paragraph; this batch's duplicate paragraph was dropped at integration and that
entry is covered by the 10.8.1 text.
