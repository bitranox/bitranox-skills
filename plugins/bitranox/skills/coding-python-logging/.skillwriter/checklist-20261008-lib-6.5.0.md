# skill-writer checklist - coding-python-logging (2026-10-08, lib_log_rich 6.5.0)

Edit: three behaviours changed by lib_log_rich 6.5.0 are restated in four places (SKILL.md install
block and Windows service line, configuration.md console_styles keys, sinks-and-deployment.md
Windows Event Log and Windows service, runtime-and-integration.md custom console adapter). Twin of
`libs/lib_log_rich/skills/python-logging`, identical apart from the `name:` line.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval with quote-back on the four changed statements, plus a
      text check of the skill files old against new.

## RED
- [x] `redcheck --corpus-cascade` returned `inherited` (strong): the machine's cascade shares the
      scenario's vocabulary, so a behavioural RED cannot fail honestly. Route taken: a text check of
      the artifact. The old text asserts all three false claims ("not declared", mixed keys
      "refused", no-flush "shutdown() raises AttributeError") and none of the true ones.

## GREEN
- [x] Text check on the new text: the three false claims are absent, the three true ones present.
- [x] Every new claim executed against lib_log_rich 6.5.0: `uv pip compile --extra eventlog`
      resolves `pywin32==312` for windows and nothing for linux; a mixed
      `{LogLevel.INFO: "green", "error": "red"}` resolves to INFO green and ERROR red; a factory
      adapter without `flush` makes `init()` raise the quoted `TypeError`, leaves no runtime and no
      thread, and `validate_config()` never calls the factory.
- [x] Quote-back probe (no tools, sonnet, four questions incl. the 6.4.2 cases): every answer a
      direct quote of the new text, none NONE.

## REFACTOR
- [x] Skill gaps reported and decided:
      - Declined: "the text does not say the extra is absent on 6.4.2" - the version stamp plus
        "before that, `pip install pywin32`" is the instruction a reader needs.
      - Declined: "the exact INFO plus 'error' mix is not shown" - the sentence covers any mix.
      - Declined: "whether the factory is called lazily" - the sentence names `init()` as the refusal
        point, which is the actionable fact.
      - Declined: "non-Windows behaviour of the extra" - "pulls pywin32 on Windows" states it; the
        section is already marked as read from the source.
- [x] RED vs GREEN diffed both ways: no statement other than the four was changed.

## Quality
- [x] Each changed line names the version it holds from (>= 6.5.0) and what earlier versions do.
- [x] No description or routing change; ASCII only; no private paths or addresses.
