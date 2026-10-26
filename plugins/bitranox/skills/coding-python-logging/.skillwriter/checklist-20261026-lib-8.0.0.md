# skill-writer checklist - coding-python-logging (2026-10-26, lib_log_rich 8.0.0)

Edit: the skill describes lib_log_rich 8.0.0. `ConsoleTheme`, `DumpFormat`, `FormatPreset` and
`GraylogProtocol` import from `lib_log_rich` as well as `lib_log_rich.domain`; `dump()` refuses a plain
string for `theme` and `console_format_preset`, `logdemo()` for those two plus `dump_format_preset`
(`TypeError: theme must be a member of ConsoleTheme, got 'neon'`); `RuntimeConfig` refuses an unknown
keyword and `payload_limits` an unknown key (`Extra inputs are not permitted`); the CLI root-options
table is complete and any other root option is a usage error; `AsyncQueueConsoleAdapter` binds to the
loop running at construction or to `loop=` and hands a cross-thread `emit` over with
`call_soon_threadsafe`; `queue_stop_timeout` is `flush()`'s default wait (timeout raises, the worker
keeps the events) as well as `shutdown()`'s drain deadline (events still queued are dropped). Twin of
`libs/lib_log_rich/skills/python-logging`, identical apart from the `name:` line.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval probes with quote-back on a copy of the files, RED on the
      pre-edit text, GREEN on the edit, each fix round re-probed on opus and haiku.

## RED
- [x] Every new statement executed against the 8.0.0 package first, and its message quoted from the
      run: top-level enum import, the two `ValidationError`s, the `dump()`/`logdemo()` `TypeError`s,
      `No such option '--queue-stop-timeout'.`; `flush()`'s default from `queue_stop_timeout` read in
      `runtime/_composition.py`, its timeout path (`wait_until_idle`, `TimeoutError`) in
      `application/use_cases/shutdown.py`.
- [x] Retrieval probe on the pre-edit text (opus, 7 questions): Q1 answered wrong ("No. Import both
      from `lib_log_rich.domain`"), Q4 and Q5 answered with the refuted behaviour (unknown
      `payload_limits` key "silently ignored"; `--queue-stop-timeout` "accepted but does nothing"),
      Q2, Q3, Q6, Q7 NONE. The edit is the change under test, so a text arm on the old files is the
      baseline; no behavioural arm, since the installed skill is the old version.

## GREEN
- [x] Same 7 questions on the edited text, opus and haiku (14 cells): Q1, Q2, Q3, Q6, Q7 answered by
      direct quote on both tiers.
- [x] Round 2 after fixes, 8 questions (flush default added), opus and haiku (16 cells): all answered
      by direct quote, no contradiction between files.
- [x] Round 3, the three touched points (dump vs logdemo presets, factory at `init()`, flush vs
      shutdown on timeout), opus and haiku (6 cells): all answered by quote.
- [x] Round 4, the two last wording fixes, opus at effort medium.
- [x] Tables canonical (`reformat_tables.py --check`); history-phrase finder: one hit, Python's
      `multiprocessing` default "before 3.14", a statement about Python, not this skill's history.

## REFACTOR
- [x] Closed:
      - configuration.md still said unknown `payload_limits` keys are ignored (validate_config
        paragraph); now refused, pointing at Payload limits.
      - CLI root-options table not declared complete; now "every root option apart from `--help`",
        any other one exit 2.
      - runtime-and-integration.md import map omitted the root enums.
      - The preset `TypeError` text was not quoted; both messages now quoted in the logdemo section.
      - `queue_stop_timeout` row in configuration.md named `shutdown()` only; it is also `flush()`'s
        default wait.
      - runtime-and-integration.md said events are dropped on expiry for `flush()` too; `flush()`
        raises and the worker keeps them.
      - SKILL.md listed `dump_format_preset` for `dump()`, which has no such argument; the sentence
        now names each function's parameters.
      - The async adapter text did not say a `console_adapter_factory` runs at `init()`; it does.
      - sinks-and-deployment.md said queued Graylog events are not lost on `shutdown()` without the
        drain deadline.
- [x] Declined, with reasons:
      - Order of the `TypeError` against other `dump()` checks, and the exact wake-up mechanism behind
        "may not wake": asyncio and call-order internals the reader does not act on; the fix is stated.
      - Whether `queue_enabled=False` avoids the cross-thread case, and which loop to pass as `loop=`
        under `asyncio.run`: the stated fix (build it and call `init()` inside `main()`) covers the
        case; an unverified alternative is not added.
      - What `flush()` does with the console and Graylog after a timeout, whether `shutdown()` raises
        on overrun, and a flush-timeout diagnostic: not changed by 8.0, and unverified here.
      - Round 4 gaps: the `dump_format_preset` message text (same pattern as the two quoted), how slow
        Graylog sends interact with the shutdown deadline, what "flushes adapters" does for Graylog, and
        whether a deadline drop reports a count: inferences outside this edit, owned by the existing
        Graylog and diagnostics text.
- [x] The rounds 1-3 quote-back dispatches ran without an explicit `effort` field; round 4 ran at
      opus, effort medium, as the review-dispatch rule requires.
