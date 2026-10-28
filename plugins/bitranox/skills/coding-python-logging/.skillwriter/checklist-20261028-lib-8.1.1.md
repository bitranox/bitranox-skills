# skill-writer checklist - coding-python-logging (2026-10-28, lib_log_rich 8.1.1)

Edit: `sinks-and-deployment.md`, journald section. The adapter maps each context or per-call `extra`
key to a field name journald accepts (`A-Z`, `0-9`, `_`, at most 64, no leading digit or `_`): other
characters become `_`, a leading digit or `_` gets the `EXTRA_` prefix, the name is cut to 64; a
clash adds `EXTRA_` while the name is taken, so no value is overwritten. Twin of
`libs/lib_log_rich/skills/python-logging`, identical apart from the `name:` line. Frontmatter
unchanged.

## PLAN
- [x] Skill type: reference. Test: RED as a text check of the pre-edit file (an EDIT; the installed
      copy is the old text), GREEN as a quote-back retrieval probe on the edited file.

## RED
- [x] Each claim checked against the code and tests first: `tests/adapters/test_journald_adapter.py`
      (mapping cases, clash cases, a datagram through `encode_journal_fields`), and a probe that sent
      the mapped event to the real journal and read every mapped field back.
- [x] Text check of the pre-edit file: 0 matches each for `64 characters`, `EXTRA__X`,
      `no value is overwritten`; control `journalctl` 6 before and after.

## GREEN
- [x] Quote-back probe, opus (effort lower), five questions on the edited file: Q1-Q4 answered by
      verbatim quote (each found once in the file; a planted non-sentence 0), Q5 (a fact the file
      does not hold) answered NOT IN FILE.
- [x] Gaps: none.
- [x] Non-ASCII: none added. Frontmatter parses (`name`, `description` only); description untouched.
