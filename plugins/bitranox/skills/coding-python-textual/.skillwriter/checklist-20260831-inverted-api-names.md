# skill-writer checklist - coding-python-textual (2026-08-31, four inverted API names)

Change: a new section, "Names that behave the opposite way from how they read", placed before the
routing tables so a reader meets it early. Four Textual API names whose behaviour is the opposite of
their reading, plus one that is NOT a trap, recorded because it is the natural thing to distrust
once the other four have burned you.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. This skill is a routing hub over vendored Textual
      docs; pre-change it had no behavioural content at all, so nothing in it could warn a reader.
      A `grep` for `check_action`, `RowHighlighted` and `App.display` outside the vendored upstream
      returns nothing.
- [x] Measured on textual 8.2.8, and the version is stated in the section, so a reader can retest.
      Three of the four cost a real defect.
- [x] GREEN: each row separates what the name READS as from what it DOES, because that gap is the
      whole failure - the code runs, and the wrong behaviour surfaces as a styling or data problem
      somewhere else entirely.
- [x] The non-trap row (`overflow-x: auto` resolving to `virtual_size.width > width`) is labelled as
      working exactly as documented, so the section does not teach blanket suspicion.
- [x] Scope: shared - library behaviour, identical for every user of that version.
- [x] Security scan: prose and API names only.
- [x] CSO description: unchanged. `DataTable`, `reactive attributes` and `TCSS styling` are already
      triggers, and all four entries sit under them.
- [x] Token budget: this is a reference/hub skill whose body is a routing index; one compact table
      is added and the routing tables are untouched.
