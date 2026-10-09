# skill-writer checklist - coding-python-logging (2026-10-08, lib_log_rich 6.5.1)

Edit: lib_log_rich 6.5.1 refuses Graylog enabled without an endpoint. The statement that it was
accepted and built no sink is replaced in four places (SKILL.md "Defaults that bite" row,
configuration.md validate_config table and closing paragraph, sinks-and-deployment.md Graylog
section and production checklist item 5). Twin of `libs/lib_log_rich/skills/python-logging`,
identical apart from the `name:` line.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval with quote-back on the changed statements, plus a text
      check of the skill files old against new.

## RED
- [x] `redcheck --corpus-cascade` returned `inherited` (strong): the machine's cascade shares the
      scenario's vocabulary (`init`, `lib_log_rich`, `startup`, `systemd`), so a behavioural RED
      cannot fail honestly. Route taken: a text check of the artifact. The old text asserts the false
      claim in four phrasings ("builds no sink and raises nothing", "no error anywhere", "which is
      accepted and builds no sink", "Graylog enabled without an endpoint is accepted"), each found
      once in the old text, and does not state the refusal.

## GREEN
- [x] Text check on the new text: each of the four false phrasings is absent; the refusal message is
      present twice and every changed statement names 6.5.1.
- [x] Every new claim executed against the library at the 6.5.1 code: `validate_config()` with
      `enable_graylog=True` and no endpoint raises `Invalid runtime settings: Graylog is enabled but no
      endpoint is set (graylog_endpoint or LOG_GRAYLOG_ENDPOINT)`, as does TLS over UDP with no
      endpoint; `init()` raises the same message for the config and for `LOG_ENABLE_GRAYLOG=1`, and an
      endpoint from `LOG_GRAYLOG_ENDPOINT` satisfies it (library tests
      `tests/runtime/test_validate_config.py`, REFUSED and ACCEPTED tables).
- [x] Quote-back probe (no tools, sonnet, four questions incl. the 6.5.0 behaviour and the unchanged
      unreachable-server case): every answer a direct quote of the new text, none NONE.

## REFACTOR
- [x] Skill gaps reported and decided:
      - Declined: "LOG_ENABLE_GRAYLOG is not named" - the probe saw excerpts only; the skill's deploy
        block and configuration reference name it.
      - Declined: "no excerpt says init() raises ValueError" - configuration.md states validate_config
        "raises the same `ValueError`" as `init()`.
      - Declined: "whether new LOG_* values are in os.environ at reload time" - owned by the existing
        validate_config text, unchanged by this edit.
      - Declined: "does an empty endpoint count" - measured: an empty `LOG_GRAYLOG_ENDPOINT` reads as
        unset and is refused with the new message; `("", 12201)` is refused by the existing host check
        (`endpoint: Graylog endpoint host must be non-empty`), so no case escapes and the text needs
        no addition.
- [x] RED vs GREEN diffed both ways: no statement other than the four was changed.

## Quality
- [x] Each changed line names the version it holds from (6.5.1) and what earlier versions did.
- [x] No description or routing change; ASCII only; no private paths or addresses.
