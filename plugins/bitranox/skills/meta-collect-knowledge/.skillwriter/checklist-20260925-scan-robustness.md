# skill-writer checklist - meta-collect-knowledge (scan robustness, exit codes)

Change: two sentences in SKILL.md. Step 1 now names the explicit `CANDIDATES: 0 (not scanned:
<reason>)` line and says an unreadable or undecodable note is skipped and named on stderr. Step 5
adds exit 2 (error) to `--seen` and says `--mark` exits 2 when it could not write the record.

## PLAN

- [x] Skill type: technique (a procedure driven by one script's output and exit codes).
- [x] Test approach: the documented outcomes are pinned by tests in `tests/test_gather_scan.py`
      that run `main()` and assert the exit code and the printed line. Recorded as the route.
- [x] Scope: the two passages that state the script's outcomes. Nothing else in the skill moved.

## RED

- [x] Before the fix, `--topic "the rules"` printed no CANDIDATES line at all (stderr only, exit
      0), so a reader told to read CANDIDATES had nothing to read.
- [x] Before the fix, one non-UTF-8 note ended the gather with a traceback and exit 1, which is
      also the `--seen` answer "not gathered". A failed `--mark` write exited 0.

## GREEN

- [x] `test_no_usable_keywords_prints_an_explicit_zero_candidates_line`,
      `test_walled_without_an_anchor_prints_an_explicit_zero_candidates_line`,
      `test_cli_warns_about_an_undecodable_note_and_still_reports_the_rest`,
      `test_mark_exits_two_when_the_record_cannot_be_written` and
      `test_an_unexpected_error_exits_two_not_one` pass and match the new sentences.

## REFACTOR

- [x] The stop rule ("Nothing matched -> stop") is unchanged; the new line only names the case
      where nothing was scanned, so the reader stops for the same reason and knows it.
- [x] Undecided gap list is empty.

## Quality

- [x] Present tense, no session narrative, no scratch paths.
- [x] No address, hostname or machine path added.
- [x] Frontmatter untouched: no `name` or `description` change, so no routing keyword moved.
