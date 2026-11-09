# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-08-31)

Change: a third worked example under "Define the types; never suppress or exclude the checker" - the
recursive `TypeAlias` on a pre-3.12 floor, after the existing stub-gap and lambda examples.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. The governing rule is already in this machine's
      memory index (`feedback-define-types-do-not-exclude-suppress-in-pyright`), so a behavioural
      baseline is contaminated. Pre-change the section carries two worked examples and neither is
      the recursive case, which is the third shape a reader meets and the one whose obvious
      shortcut is `Any` - a suppression wearing a type's clothes.
- [x] EXECUTED, not reviewed. Both forms were run rather than reasoned about:
      - the shipped form reports 0 errors under pyright strict at `pythonVersion` 3.10;
      - the `dict`/`list` variant reports `reportArgumentType` on `{"a": {"b": "c"}}`, and pyright
        names the mechanism itself ("Type parameter _VT@dict is invariant ... Consider switching
        from dict to Mapping which is covariant in the value type");
      - both import cleanly on 3.10, so the runtime is not what separates them.
      That control is what makes the example evidence rather than assertion: a wrong API shape here
      is accepted and falls through, so "it did not raise" would have proved nothing.
- [x] `RUF036` verified by running ruff, not recalled: `None` not at the end of the type union.
- [x] Each of the three traps is stated with WHERE it reports, because none reports at its cause -
      the runtime-import one fails only on import, so a type-check-only run stays green.
- [x] Scope: shared - language and checker semantics on any pre-3.12 floor.
- [x] Security scan: the example is a generic JSON value type; no paths, hosts or private names.
- [x] CSO description: unchanged; "eliminate dict parameters" and "make a Python data flow type-safe
      end to end" already cover retrieval.
- [x] Token budget: one worked example in a reference skill that is already example-led.
