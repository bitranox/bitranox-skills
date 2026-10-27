# skill-writer checklist - coding-python-logging (2026-10-27, lib_log_rich 8.0.3)

Edit: the skill describes lib_log_rich 8.0.3. `exc_info` is the formatted traceback text
(`traceback.format_exception`), ready-made text in `extra["exc_info"]` moves into the event's `exc_info`
field, a string `exc_info` argument is ignored; frames are compacted by frame (`frames_removed` is the
sum over all runs) and an over-long text keeps its END behind `[truncated]…`; non-UTF-8 `bytes` in a JSON
dump's `extra` are hex. Corrected from the source: `shutdown()` raises and leaves the runtime initialised
when the queue does not drain in time; all five `DropReason` members; the GELF fields (`_request_id`
sent, context `extra` not sent); a checkpointed `dump()` moves the whole buffer; signal handlers set a
flag or raise `SystemExit`, SIGINT needs none. Twin of `libs/lib_log_rich/skills/python-logging`,
identical apart from the `name:` line. Frontmatter unchanged.

## PLAN
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: RED as a text check of the pre-edit file (an EDIT; the installed copy
      is the old text), GREEN as a quote-back retrieval probe on the edited files.

## RED
- [x] Each new claim checked against the code or a run before it went in: the `exc_info` text, the
      string argument and `extra["exc_info"]` (run: the text lands in `exc_info`, `extra` is `{}`),
      the frame compaction and tail cut (`_payload_sanitizer.py`, new tests), the hex bytes
      (`_schemas.py`, pinned beside enum, dataclass, datetime, timedelta and bytearray output),
      `QUEUE_FAILURE` (`process_event.py` `_interpret_queue_outcome`).
- [x] Text check of the pre-edit files: 0 matches each for `QUEUE_FAILURE`, `_request_id`,
      `configured_styles`, `frames_removed`, `SystemExit`, the runtime staying initialised, the
      kept END; 1 for the WHOLE buffer, 2 for `adapter_error`; control `shutdown` 56.

## GREEN
- [x] Quote-back probe, opus (effort medium) and haiku, nine questions on the edited files: both
      tiers answered Q1-Q8 correctly; each quote found verbatim in the files (one hit each), a
      planted non-sentence 0. Q9 (non-UTF-8 bytes in a JSON dump) NOT IN SKILL on both: a real gap.
- [x] Gaps closed: Q9 stated in dumps-and-cli.md; where `extra["exc_info"]` text lands; what
      `frames_removed` counts across several runs; the exception-line-longer-than-the-limit case;
      what `QUEUE_FAILURE` means; SIGINT needs no handler.
- [x] Re-probe on the corrected text (opus, effort medium, six questions on exactly those points):
      all six answered by quote. Its last three wording notes applied ("without being re-formatted",
      the same exception-line wording in dumps-and-cli.md, valid UTF-8 bytes written as text).
- [x] Gaps declined: the checkpoint file's encoding of bytes (not verified, so not claimed); a call
      passing both `exc_info=True` and `extra["exc_info"]`; whether `drops_by_reason` lists every
      member (the example is a measured run, not the schema).
- [x] Non-ASCII: only the library's own `…[truncated]` / `[truncated]…` markers, quoted verbatim.
      Frontmatter parses (`name`, `description` only); description untouched (489 characters).
