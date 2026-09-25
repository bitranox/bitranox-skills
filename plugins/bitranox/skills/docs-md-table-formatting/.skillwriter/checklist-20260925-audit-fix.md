# skill-writer checklist - docs-md-table-formatting (2026-09-25, skill-script audit fixes)

Change: the SKILL.md text is corrected only where `reformat_tables.py` and `tablekit.py` changed
documented behaviour. The body gains the exit-code table, the GFM rule for a pipe inside a code
span, and the list of layouts the formatter now preserves (indentation, line endings, BOM, nested
and indented code). The tablekit section states its refusals and exit codes.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] Route: a TEXT CHECK of the artifact against the scripts' executed behaviour, not a
      behavioural subagent arm. These are reference corrections whose truth is decided by what the
      script does, so the evidence is the script run, and every claim added is pinned by a test.
- [x] RED: the old sentence "handles pipes inside backtick spans" told a reader that `` `a | b` ``
      in a cell is safe. GFM splits it (the spec's escaped-pipe example; pandoc -f gfm renders the
      row with the last cell dropped), and `--strict` then passed a content-losing row. The script
      test `test_strict_fails_a_row_whose_code_span_pipe_drops_a_cell` fails on the old script and
      passes on the new one.
- [x] GREEN: each new sentence quoted back against a test that executes it - exit 2 for usage and
      unreadable files (`test_cli_unknown_option_exits_2`, `test_a_non_utf8_file_...`), `-r` skips
      a directory named `*.md` (`test_recursive_skips_a_directory_named_md_...`), indentation kept
      (`test_a_table_nested_in_a_list_item_keeps_its_indentation`), indented code left alone,
      CRLF and BOM kept, display width.
- [x] Lost-result check: the old "leaves a table with inconsistent column counts alone" and the
      ragged-row paragraph are kept unchanged; nothing the section said before was removed.
- [x] Real-table regression: tables copied verbatim from shipped skill docs are byte-identical
      after a pass (`tests/fixtures/real_tables.md`), and a differential over every tracked
      markdown file in this repo shows zero byte changes between the old and new formatter.
- [x] Description unchanged, so no routing keyword moved.
- [x] Security scan: fixtures are tmp_path or copied doc tables; no hosts, addresses or private
      paths added.
