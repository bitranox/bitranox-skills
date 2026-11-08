# Review checklist 2026-11-08: [run] unattended_note and the ended-with-a-question flag (meta-skill-ab-test)

Change: `[run] unattended_note` (optional text) is appended to every arm's prompt alike after a
blank line (`RunContext.prompt`), the bare arm's included; `arm_meta` adds
`unattended_note_sha256` to every journal row and `result.json`. `StreamAccount.last_text` holds
the session's last model text (a tool_use-only record keeps the earlier text, a CLI synthetic
notice is skipped) and the dispatch summary carries it. `score` reads it from the kept
`stream.jsonl` into `last_text` and `ended_with_question`, flags a true one on the arm's line and
in `--json` `flags` (joined with a store flag by "; "), and never voids. SKELETON and EPILOG list
the note; SKILL.md gains one bullet under "Before and during a live run". Existing score and
result keys are unchanged; the score key-set test gains `last_text` and `ended_with_question`.
The description is untouched.

## Claims and their evidence

- [x] Description unchanged (no frontmatter line in the diff); SKILL.md, the scripts and the
      tests are ASCII only (non-ASCII byte scan printed nothing).
- [x] RED, code: on the old source the 22 new or changed tests failed (`'StreamAccount' object
      has no attribute 'last_text'`, `'Run' object has no attribute 'unattended_note'`, the
      unknown key loading silently so `DID NOT RAISE ProfileError`, `KeyError:
      'unattended_note_sha256'` and `'ended_with_question'`, the prompt without the note, the
      key-set test). `mutation_arm.py --revert` of the four scripts to HEAD reports KILLED for
      `test_score_flags_an_arm_that_ended_by_asking_and_still_counts_it` (`KeyError:
      'last_text'`), and of abtest.py and abprofile.py for
      `test_the_unattended_note_reaches_every_arms_prompt_and_every_record_names_it`.
- [x] Mutation battery (`mutation_arm.py --battery`, baseline green first and last), 15 of 16
      arms KILLED: a tool_use record clearing last_text, last_text set after the id dedupe (a
      later text block of the same message lost), a synthetic notice counted, summary dropping
      last_text, no text reading as false, strict decoding, the note not appended, no blank line,
      the sha not recorded, either flag dropped from the joined line, the flag showing the start
      of a long text, and the three profile checks. The survivor, `text.rstrip().endswith("?")`
      against `text.endswith("?")`, was dead code: `_text_of` already collapses whitespace, so
      the `rstrip` was removed rather than tested.
- [x] Executed, not reviewed: three live fake-claude arms (C, V1, a bare arm) receive
      `<task>\n\n<note>\n` with the same note and the same sha in every journal row and
      `result.json`; without a note the prompt is the task alone and the sha is null; a stream
      ending "Shall I start?" scores `ended_with_question: true`, `void: []` and the flag on the
      text line and in `--json` `flags`; a bad byte in the stream costs its line, not the last
      words. Full suite with CI's dependency set: 423 passed, 1 skipped.
- [x] RED, text: the opus `baseline-probe` run for the run-lock change (pre-edit SKILL.md) held
      this change's two questions and answered NONE to both: it guessed "put the sentence in
      task.md" and that `score` does not show a question at all.
- [x] GREEN (opus x1, haiku x1, six questions: tell every arm without differing prompts and where
      it is recorded, how score shows a question, a forgotten note after the seal, a note naming
      the skill, an earlier question, a null value): every answer that the text could give a
      direct quote.
- [x] Gaps from GREEN, decided:
  - CLOSED: a note forgotten before the seal (both) - "`abtest.toml` is frozen there, so a note
    forgotten then needs a new run dir".
  - CLOSED: trailing characters and an earlier question (both) - "when its last character is
    `?`, else false; an earlier question does not count".
  - CLOSED: what null covers and a missing stream (opus) - "both are `null` when the stream is
    missing or holds no text" (`_last_words` in `scripts/abscore.py`).
  - CLOSED: the false value (opus) - "true when ... else false".
  - CLOSED: how much text the flag shows (opus) - "<at most its last 200 characters>"
    (`QUESTION_SHOWN` in `scripts/abtest.py`).
  - CLOSED: what the sha covers (opus) - "the note's own sha256".
  - CLOSED: why the note must not name the skill (both) - "or the bare arm is pointed at it".
  - DECLINED: a cross-arm check of the sha in `score` (opus) - the journal rows and
    `result.json` carry it; a consistency check is not part of this change and every arm gets
    the same sealed text by construction.
  - DECLINED: whether the last text is a block or the whole message, and subagent text (both) -
    "the session's last model text from `stream.jsonl`" names the source; subagent transcripts
    are not the stream.
  - DECLINED, probe artifact: the `--json` shape and field names (opus) - the passage was given
    alone; the score paragraph and `--help` name the fields.
- [x] Re-probe on the revised bullet (haiku, six questions on the closed gaps): every answer a
      direct quote ("so a note forgotten then needs a new run dir", "the note's own sha256",
      "an earlier question does not count", "both are `null` when the stream is missing or holds
      no text", "<at most its last 200 characters>", "or the bare arm is pointed at it"). Its
      leftover gaps are DECLINED: trailing whitespace (`last_text` is "one line", which
      `_text_of` makes by collapsing whitespace, so none remains), the hash encoding and the
      character unit (implementation detail no reader acts on differently), tool output or
      thinking as model text (only text blocks are "model text"), and a note added after the
      seal but before any run (covered by "`abtest.toml` is frozen there").
- [x] Width and fence check over the added lines printed nothing; the bullet after the insertion
      point (usage windows) holds no back-reference that now binds to it.
- [x] Decisions: none - the field, the flag and their documentation follow the approved plan;
      the 200-character flag excerpt and the lenient decoding are mechanics, not choices between
      options a reader would decide differently.
