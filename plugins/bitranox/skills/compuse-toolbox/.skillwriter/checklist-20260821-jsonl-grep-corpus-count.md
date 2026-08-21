# skill-writer checklist - compuse-toolbox (corpus mode for `jsonl_grep`)

Change: `jsonl_grep` gains `--count`, which tallies a dotted field's values across every file under
the paths given and walks the `*.jsonl` below a directory. Existing script, existing table row; no
new tool, no new skill.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale). This ENHANCES a shipped jig,
      which is what the skill's own "Building or enhancing a jig" section asks for when a jig falls
      short in use.
- [x] Trigger is measured, not hypothetical: "which values does this field take across the whole
      transcript corpus, and how many records carry each" is a question the shipped tool could not
      answer, because it read one file and could not count. Reaching for the indirect answer instead
      cost three built-and-deleted designs, about 370 lines, for a value one command now returns.
- [x] Checked the capability is not already shipped, in the tool AND its neighbours: `jsonl_grep`
      took a single path or stdin and had no aggregation; `transcript_tail` is single-file and
      returns turns, not tallies; `claim_check` answers present/absent over a file set, never what
      values a field holds. No other jig in the table reads a corpus.
- [x] Scope: one core function plus a path expander and a streaming reader in the existing script,
      tests, one table row rewritten, one rationale bullet, CHANGELOG, version bump.

## RED
- [x] 12 tests written against the contract, then run against the pre-change script: 11 FAILED
      (`scan_corpus` absent, `--count` unrecognised), 6 pre-existing passed, and
      `test_cli_still_reads_a_single_file_without_count` passed as intended - it pins existing
      behaviour, so it must pass on BOTH versions or it is not pinning anything.
- [x] Routing RED/GREEN on the table row itself, since the tests cover the script and not the doc.
      Two inert probes (no filesystem tools), same question, same model tier, differing only in the
      `jsonl_grep` row. RED, given the old row: "No listed tool does directory-wide recursion +
      tally", then hand-rolled a 70-line stdlib script; its toolbox-native fallback would have
      launched `uv run` about 1500 times. GREEN, given the new row: the documented one-line
      invocation, and it checked the exit code because the row states `exit 3 = read nothing`.
- [x] Contamination checked before dispatch, and the first result was a hit: `redcheck
      --corpus-cascade` flagged two cascade files at 14% shared terms. The shared terms were
      generic vocabulary (`roughly`, `hold`, `values`, `transcript`), not the lesson, so the check
      was re-run at the rarity threshold its own documentation names for boilerplate hits and came
      back clean. Confirmed independently with `claim_check`: ABSENT for `jsonl_grep` with a control
      matching 46 times across 6 files, so the files were genuinely read.
- [x] The RED probe additionally loaded the INSTALLED skill (the pre-change version), so it saw the
      old text from two directions rather than one. The GREEN probe used no tools, so it answered
      from the supplied row alone.

## GREEN
- [x] 21 tests pass in the file; hooks plus compuse-toolbox suites are 2150 passed, run with CI's
      dependency set (`pytest PyYAML lxml defusedxml ruamel.yaml httpx2`), not a bare `pytest`.
- [x] Bare-environment import verified in a fresh venv holding only pytest: `orjson` absent from
      `sys.modules`, and the stdlib branch confirmed ACTIVE by its distinct output spacing rather
      than assumed - the first attempt at this check ran on an interpreter that HAS `orjson`, so it
      proved nothing and was redone.
- [x] Live run against the real corpus, not only fixtures: 1489 files in about 3 seconds, 0 skipped,
      0 unparseable lines, seven distinct values returned with counts. The empty-corpus case exits 3
      and prints `0 read`.

## REFACTOR
- [x] GREEN diffed against RED in BOTH directions. RED's hand-rolled script reported diagnostics the
      new tool did not: a count of unparseable lines. That is a lost result, not an acceptable
      trade, and it sits squarely in this tool's own thesis that a shrinking denominator must never
      be silent - so `--count` now counts unusable lines and reports them on stderr.
- [x] Writing that test surfaced a latent crash: a line that parses but is not an object (a bare
      array) reached `obj.get(...)` and raised `AttributeError`, which would abort a 1500-file scan
      outright. Now counted as unusable like any other bad line.
- [x] Gaps GREEN reported, closed in the row it actually reads: recursion was a guess (now stated as
      "walks the `*.jsonl` below `<dir>`"), whether `--type` composes with the corpus form was
      unconfirmed (the example now shows `--type assistant`), and the field syntax was a generic
      placeholder (now the worked `--field message.model`).
- [x] Gaps DECLINED, with reasons: the script's absolute location is the shared convention of all 17
      rows and the skill announces its base directory, so a per-row path would be noise; sidechain
      filtering belongs to `transcript_tail`, which carries the record-shape knowledge, and `--role`
      already composes here; a separate bucket for records missing the field is not a data defect
      but the ordinary meaning of "no value", unlike an unparseable line.

## Design decisions
- [x] Exit 3 for a corpus that read nothing, matching the convention `redcheck` already uses in this
      skill. A negative is the dangerous result: "the field holds nothing" and "I never really
      looked" print identically, so a mistyped path must be loud.
- [x] Reach diagnostics go to stderr, never into the parsed stream - a file count in stdout would be
      read as data. A test asserts the count is in stderr and absent from stdout.
- [x] A path that does not exist contributes nothing rather than raising, because `files_read` is
      already the number that decides whether an answer was earned.
- [x] Files stream line by line rather than loading whole; transcripts run to hundreds of MB and a
      corpus scan opens 1500 of them.
- [x] The list mode now reads EVERY path given. It previously read only the first and exited 0,
      which is exactly the silent truncation this toolbox exists to prevent.
- [x] Unreadable files are listed as skipped rather than dropped, so a permission problem cannot
      shrink the corpus quietly.

## Quality
- [x] Existing behaviour preserved: `filter_records` keeps its signature, return shape and
      semantics, now sharing the per-line matcher with the streaming reader; a test pins the
      single-file CLI path.
- [x] Import-safe core functions (`scan_corpus`, `expand_paths`, `iter_file_matches`); all run-time
      work stays behind `if __name__ == "__main__":`.
- [x] ASCII only in the script, the tests, the SKILL.md edit, the CHANGELOG entry and this file;
      verified by byte scan, no matches above 127.
- [x] No hostnames, addresses, usernames or private paths in the change; the live-run evidence is
      recorded as counts only, and no transcript content was copied into any file.
- [x] Present tense, no session narrative in the shipped text.

## Deliverables
- [x] `scripts/jsonl_grep.py` (corpus mode, streaming reader, path expander, unusable-line count),
      `tests/test_jsonl_grep.py` (21 tests, 15 new), SKILL.md table row + rationale bullet.
- [x] `plugin.json` bumped 5.218.3 -> 5.219.0 (MINOR: a new capability in an existing skill);
      CHANGELOG entry added. `docs/skills.md` and `skill_triggers.json` regenerate byte-identical,
      because the frontmatter description is unchanged - recorded rather than assumed.
