# skill-writer checklist - coding-python-logging (2026-10-28, lib_log_rich 8.1.0)

Edit: the skill describes lib_log_rich 8.1.0. Every sink shows an event's `exc_info` / `stack_info`
text, `exc_info` first, joined by a newline: indented four spaces under the line on the console and in
the text and HTML text dumps, an HTML-escaped `<pre>` in the HTML table's message cell, GELF
`full_message`, journald `MESSAGE` plus `EXCEPTION_TEXT` / `STACK_TEXT` (reserved), Windows Event Log
`exc_info=` / `stack_info=` strings. The scrubber does not touch the text. A queue console adapter
without `console_width` puts each event, traceback included, in one segment. Twin of
`libs/lib_log_rich/skills/python-logging`, identical apart from the `name:` line. Frontmatter unchanged.

## PLAN
- [x] Skill type: reference. Test: RED as a text check of the pre-edit files (an EDIT; the installed
      copy is the old text), GREEN as a quote-back retrieval probe on the edited files.

## RED
- [x] Each claim checked against the code and the new tests first: `tests/adapters/test_traceback_rendering.py`
      (18 tests through the real adapters; Graylog over a real UDP socket), and a review that sent the
      journald fallback datagram to the real journal and read it back.
- [x] Text check of the pre-edit files: 0 matches each for `full_message`, `EXCEPTION_TEXT`, `STACK_TEXT`,
      `indented four spaces`, `message cell`; control `shutdown` 60 before and after.

## GREEN
- [x] Quote-back probe, opus (effort medium), six questions on the edited files: Q1-Q5 answered by
      verbatim quote (each found once in the files, a planted non-sentence 0). Q6 (queue segments
      per event) NOT IN SKILL: a real gap.
- [x] Gaps closed: Q6 stated (one segment without `console_width`, wrapped lines with one); journald
      and GELF now say both texts are joined by a newline, `exc_info` first; the HTML table cell is an
      HTML-escaped `<pre>`.
- [x] Gaps declined: whether `ExportStyle.HTML` queue output escapes traceback text - the skill
      already marks that output as trusted-only.
- [x] Non-ASCII: none added. Frontmatter parses (`name`, `description` only); description untouched.
