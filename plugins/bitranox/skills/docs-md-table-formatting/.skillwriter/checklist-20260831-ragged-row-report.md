# skill-writer checklist - docs-md-table-formatting (2026-08-31, ragged rows are reported)

Change: `reformat_tables.py` reported a table whose row cell-count does not match its header as
`Unchanged`. It now names every such row on stderr with file and line, carries the count in the
status line, and gains `--strict` to exit non-zero for CI.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: 6 tests written first and watched fail. One of them - `--strict` on a ragged file must
      exit 1 - PASSED in the RED run for the wrong reason: the option did not exist, so the tool
      exited 1 with "Unknown option". The control (`--strict` on a CLEAN file must exit 0) is what
      caught that, and it is in the suite permanently for the same reason.
- [x] The defect being fixed is the report, not the bail. Leaving a ragged table alone is correct -
      the tool can only align what parses. Printing `Unchanged` for it is the bug, because that
      reads as a clean bill of health for the one shape the tool cannot repair.
- [x] BOTH DIRECTIONS, and they differ. A row with MORE cells than the header loses the surplus;
      a row with FEWER is PADDED and loses nothing. The first message claimed content loss for
      both, which is wrong half the time - the exact way a warning trains its reader to ignore it.
      Found by running the tool over this plugin, not by review. Two tests now pin the two messages.
- [x] Not-a-table is not a finding: without a valid separator row the detector returns empty, so
      the real findings are not buried in noise. A test pins it.
- [x] Default exit codes are unchanged, so existing callers keep their semantics; `--strict` is
      opt-in for CI.
- [x] First real sweep over this plugin found 3 ragged rows: one in this repo's own
      `coding-python-rpyc` routing table (third column missing on one row, now restored) and two in
      VENDORED upstream Textual docs, which are deliberately left alone - editing a vendored copy
      would make it disagree with its source.
- [x] Tests: 52 pass.
- [x] Scope: shared - GFM table semantics.
- [x] Security scan: fixtures are tmp_path; no hosts, addresses or private paths.
- [x] CSO description: unchanged; "table columns look misaligned" and "reviewing markdown files that
      contain tables" already cover retrieval.
