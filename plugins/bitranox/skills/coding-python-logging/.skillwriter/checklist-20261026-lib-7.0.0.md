# skill-writer checklist - coding-python-logging (2026-10-26, lib_log_rich 7.0.0)

Edit: the skill describes lib_log_rich 7.0, which types its public API. Examples pass enum members
(`ConsoleStream`, `ConsoleTheme`, `FormatPreset`, `GraylogProtocol`, `QueuePolicy`, `DumpFormat`,
`ExportStyle`, `DropReason`); `RuntimeConfig(...)` refuses an unknown enum value with a
`ValidationError`; `bind()` takes only the context fields plus `extra={...}`; `ContextSnapshot` and
`dump_context_snapshot` / `load_context_snapshot` carry context to a child; `enable_dotenv(...,
dotenv_override=True)` replaces `load_dotenv`; ring-buffer persistence is only for code that builds
`RingBuffer(checkpoint=JsonlCheckpoint(path))`. The stdlib-bridge bullet says `lib_log_rich.*`
warnings reach `logging.lastResort` when only bridges would see them. Every version-scoped line is
rewritten as current behaviour. Twin of `libs/lib_log_rich/skills/python-logging`, identical apart
from the `name:` line.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: a text check of the old against the new files, every changed
      example executed and type-checked, and a quote-back probe on the changed statements.

## RED
- [x] `redcheck --corpus-cascade` on a scenario covering the changed calls returned inherited
      coverage on term overlap only (`console`, `lib_log_rich`, `logging`, `variables`); the named
      documents do not state the 7.0 calls. Route taken anyway: a text check of the artifact.
- [x] Text check, pre-edit text against the edit (counts of each claim the 7.0 library refutes):
      `load_dotenv(` 1 -> 0; `CONSOLE_PRESETS` 1 -> 0; `Unknown console format preset` 2 -> 0;
      `export_style="ansi"/"html"` 2 -> 0; `theme="..."` argument 1 -> 0; `graylog_protocol="..."`
      argument 1 -> 0; unknown `console_theme` described as accepted 1 -> 0; version-history lines
      (`>= 6.`, `Before 6.`, `from 6.x`, `earlier versions`) 22 -> 0. The remaining string values
      (`console_stream="custom"`, `"none"`, `"bogus"`, `dump(dump_format="json")`) are prose about
      `RuntimeConfig` value strings, which still parse, or a `str | DumpFormat` argument.
- [x] Against the 7.0 library the removed text fails: `config.load_dotenv` does not exist,
      `QueueConsoleAdapter(export_style="ansi")` raises `TypeError`, `bind(order_id=...)` raises
      `TypeError`.

## GREEN
- [x] All 23 Python blocks extracted and checked with pyright strict at Python 3.10 against the
      package: 0 type errors (the two left are a deliberate fragment's undefined `logger`).
- [x] Every changed claim executed against the 7.0 package: every `RuntimeConfig` and `LOG_*`
      refusal message quoted, dump presets and formats, `bind` `TypeError`, snapshot pickle and
      text round trip in a spawn child, `export_style` `TypeError`, queue policies, `lastResort`
      behaviour, `flush(flush_ring_buffer=True)` leaving the buffer intact through `init()`, and
      UDP plus TLS accepted with Graylog off and refused with Graylog enabled with an endpoint.
- [x] Quote-back probe, 7 questions, opus and haiku (2 tiers, 14 cells): every answer a direct
      quote of the new text, each quote found verbatim in the files; the version question (when
      TLS over UDP was first refused) answered NONE on both tiers, so no version history remains.

## REFACTOR
- [x] Closed: SKILL.md stated TLS over UDP as refused unconditionally while configuration.md and
      sinks-and-deployment.md scoped it to Graylog enabled with an endpoint, and no file stated the
      Graylog-off case. Both files now state the same condition and that Graylog off accepts it.
- [x] Declined, with reasons:
      - Exact keyword-form message for an unknown `console_theme`: configuration.md quotes a sample
        `ValidationError` and states one entry per bad field; the field-specific text is pydantic's.
      - `enable_dotenv` calls with different override flags, `deserialize` replace-or-merge,
        `RingBuffer(checkpoint=...)` wiring, `enable_dotenv` after `init()`: unchanged by 7.0 and
        owned by the existing text; outside this edit.
      - `ExportStyle` members not listed: the enum has exactly `ANSI` and `HTML`, both named.
      - Bind-level `extra` versus per-call `extra`: runtime-and-integration.md places each.
      - TLS-over-UDP: error order when it combines with a missing endpoint, a refusal-table row,
        the CLI combination, a DTLS rationale: not changed by 7.0, the rule is stated in prose
        beside the table.
- [x] Final re-probe on the final text (haiku, the TLS questions): Graylog off - "With Graylog off
      the combination is accepted." (configuration.md, and the same in SKILL.md); Graylog enabled
      with an endpoint - refused, quoted from all three files; SKILL.md and configuration.md state
      the same condition; "No direct contradictions were found between the five files on this
      rule." Its remaining gaps (no refusal-table row, precedence with the missing-endpoint
      refusal, the env-variable and CLI forms, whether Graylog-off warns) are the ones declined
      above. No new undecided gap.

## Quality
- [x] Describes only the latest release: the finder and a version-number grep return no history.
- [x] No description or routing change; ASCII only; tables canonical (reformat_tables --check);
      no private paths or addresses.
