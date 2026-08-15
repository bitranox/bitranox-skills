# skill-writer checklist - compuse-toolbox (whole-transcript modes for `transcript_tail`)

Change: `transcript_tail` gains `--all` (every user/assistant text turn) and `--tool NAME` (every
`tool_use` of one tool, with its input), each row carrying the JSONL line number it came from, plus
a `--json` envelope. Existing script, existing table row; no new tool, no new skill.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale). This change ENHANCES a shipped
      jig rather than adding one, which is what the skill's own "Building or enhancing a jig"
      section asks for when a jig falls short in use.
- [x] Trigger is measured, not hypothetical: reviewing a finished session needs every record, and
      the shipped tool returns only the LAST user and assistant text. Four throwaway extractors were
      hand-rolled in a single session against one transcript to get (a) every user turn with line
      numbers, (b) every assistant turn, (c) a windowed dump of block types, (d) every `Agent`
      dispatch with its `subagent_type` and `model`. The repo's own jig-repetition nudge fired on
      the fourth.
- [x] Checked the capability is not already shipped, in the tool AND in its neighbours: `tail_messages`
      was the module's only public function and keeps a single last-seen value per role; `jsonl_grep`
      filters by `--type`/`--role` and extracts a dotted `--field`, so `--field message.content`
      returns the raw BLOCK LIST, not the flattened text, and it carries no line numbers at all.
      No other jig in the table reads a transcript.
- [x] Scope: two core functions plus a shared record iterator in the existing script, tests, one
      table row rewritten, one rationale bullet, one description clause, CHANGELOG, version bump.
- [x] Not implemented, deliberately: the windowed all-block-types dump (extractor (c)). It was a
      one-off orientation aid, not a question worth a mode, and `jsonl_grep` already dumps records.

## RED
- [x] 13 new tests written against the contract, then RUN AGAINST THE PRE-CHANGE SCRIPT
      (`git show HEAD:.../transcript_tail.py` into a scratch dir with a copy of the test file and
      conftest): 12 FAILED, 5 passed. The 5 are the 4 pre-existing tests plus the new byte-identical
      pin, which is exactly the intended shape - the pin must pass on BOTH versions or it is not
      pinning anything.
- [x] The first draft of `test_cli_refuses_both_modes_at_once` passed vacuously against the old
      script: argparse exits 2 for an UNRECOGNISED flag just as it does for a mutually-exclusive
      pair, so the assertion could not tell the two apart. Fixed by asserting each flag is accepted
      ALONE first, which makes the exit 2 attributable to the exclusion; it then failed RED with the
      other 11.
- [x] Coverage: every turn returned in order with its line number (not just the last); role filter;
      line numbers verified to index the PHYSICAL file line with a blank and an unparseable line in
      between; unparseable lines reported rather than dropped, a JSON non-object counted among them;
      sidechain/meta skipped by default and kept by each flag, in both new modes; several tool calls
      in one record each getting a row with that record's line; the absent-tool and present-tool
      cases asserted TOGETHER so an always-empty implementation cannot pass the negative half alone;
      CLI text output, `--json` envelope shape, stderr warning kept out of the JSON stdout, exit 1
      on no match, exit 2 on both modes at once.

## GREEN
- [x] 17 tests pass in the file; the whole compuse-toolbox suite is 238 passed, run with CI's
      dependency set (`pytest PyYAML lxml defusedxml ruamel.yaml httpx2`), not a bare `pytest`.
- [x] Bare-environment import verified, which is this script's own historical failure: imported with
      plain `python3` in an environment where `orjson` is absent, and confirmed at runtime that
      `orjson` is not in `sys.modules` - so the stdlib fallback is the path the tests exercised, not
      a branch nobody ran.
- [x] Live run against a REAL transcript, not only pytest fixtures: a 9626-line session file.
      `--all --role user --json` returned 1790 rows, 0 skipped, with strictly increasing line
      numbers; `--tool Bash --json` returned 1188 rows; an absent tool name printed nothing and
      exited 1. Ten sampled rows (the first five and the last five) were checked by reading the
      named physical line back out of the file and requiring its `type` to equal the row's role, so
      the line numbers are verified against the file rather than against the code that produced them.
- [x] Table row names BOTH jobs (the tail and the whole-transcript extraction) and its Invoke column
      shows real values for each mode, not a placeholder.
- [x] Description clause extended with the new trigger; catalog (`docs/skills.md`) and trigger map
      (`skill_triggers.json`) both regenerated. The trigger map came out byte-identical, so the
      change adds no new router keyword; recorded rather than assumed.

## Design decisions
- [x] `--all` emits one row per RECORD, not per text block, although a record can hold several. All
      of a record's blocks share one line number, so per-block rows would repeat the locator without
      distinguishing anything; the existing `_flatten` already joins them and the tail mode uses the
      same function, so both modes report identical text for a given record.
- [x] Line numbers count EVERY physical line, blanks and unparseable ones included. A number that
      skipped them would address the parser's internal sequence rather than the file, which defeats
      the point of carrying it.
- [x] A JSON line that parses but is not an object is treated as malformed. Previously it reached
      `obj.get(...)` and raised `AttributeError`, an uncaught crash with no test on it; it is now
      counted onto the `skipped` list like any other unusable line.
- [x] `--json` was added beyond the two requested modes: the rows are structured data, and the text
      form's `== line N role ==` header is ambiguous when the transcript TEXT itself contains such a
      line, which a transcript of this work already would. The envelope matches the shape `newest`
      and `claim_check` already use in this skill.
- [x] Exit 1 on a mode that matched nothing, so an empty result is a reportable outcome instead of
      silent success. The tail mode keeps exiting 0 unconditionally, because a role never seen is a
      legitimate empty string there rather than a no-match.
- [x] `tool_uses` requires a tool NAME rather than defaulting to all tools. The measured need was
      one named tool; an all-tools listing is `jsonl_grep`'s territory and was not built on spec.

## Quality
- [x] Existing behaviour preserved: `tail_messages` keeps its signature, its return shape and its
      semantics, now reading through the shared `iter_records` iterator. The CLI with neither new
      flag produces the same two headers and bodies, asserted against a literal expected string.
- [x] One import-safe core function per mode (`all_messages`, `tool_uses`) plus the shared
      `iter_records`; all work stays behind `if __name__ == "__main__":`.
- [x] The `_dumps` helper, previously defined and never called, is now used by the tool-input and
      `--json` output paths; no dead code left behind.
- [x] Diagnostics go to stderr in both text and `--json` mode, so stdout stays parseable.
- [x] ASCII only in the script, the tests, the SKILL.md edits, the CHANGELOG entry and this file;
      verified with a byte scan for anything above 127, no matches.
- [x] No hostnames, addresses, usernames or private paths anywhere in the change. The live-run
      evidence above is recorded as counts and line numbers only; the transcript path is not named,
      and no transcript content was copied into any file.
- [x] Present tense, no session narrative in the shipped text; the measurement that motivates the
      change is stated as a fact about the tool, not as a story about a run.

## Deliverables
- [x] `scripts/transcript_tail.py` (two modes, `--json`, shared iterator), `tests/test_transcript_tail.py`
      (17 tests, 13 new), SKILL.md table row + rationale bullet + description clause.
- [x] `plugin.json` bumped 5.199.0 -> 5.200.0 (MINOR: a new capability in an existing skill);
      CHANGELOG entry added; `docs/skills.md` and `skill_triggers.json` regenerated.
