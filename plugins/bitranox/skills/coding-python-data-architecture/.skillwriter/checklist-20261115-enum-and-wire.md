# skill-writer checklist - coding-python-data-architecture (2026-11-15, plain Enum, subset name maps, output harness, ctx access)

Change: four additions. A plain `Enum` parameter (no value mixin) is coerced with `TheEnum(value)`
because `==` never matches its raw value; an `Annotated` BeforeValidator/PlainSerializer pair whose
name map covers a subset of the Enum refuses members without a wire name; a fixer changing a type
on an output wire builds its before/after harness before its first edit; and a `value_error`
item's message is read as `str(item.get("ctx", {}).get("error"))`, the form pyright strict
accepts (SKILL.md STEP C item 5 line and `references/validation-error-messages.md`).

- [x] Receipt held; this agent loaded meta-skill-writer itself
- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill
- [x] Mechanism claims executed before probing (pydantic 2.14.3, pydantic_core 2.50.4):
      `CombineMode.XOR == "xor"` is False, `CombineMode("xor")` returns the member and
      `CombineMode("nand")` raises `ValueError`; a blanket member pass-through built
      `M.model_validate({"data": {Kind.TABLEDATA: 1}})` and `model_dump_json()` raised
      `PydanticSerializationError` (KeyError); the subset validator refused it at loc
      `('data', '<Kind.TABLEDATA: 3>', '[key]')`; pyright strict reported `item["ctx"]` as
      "Could not access item in TypedDict" and accepted the `.get` form
- [x] RED (pre-edit text via `git show HEAD:`, `opus` quote-back): Skill gaps named all four as
      absent - plain Enum answered only by inference, subset name maps not covered, no WHEN for
      the before-state and no word on `git stash`, no pyright typing for `ctx`
- [x] GREEN: `opus` (effort medium) and `haiku` both quoted the new lines for all four questions
- [x] Skill gaps from GREEN: the reference showed the `.get` form without `str()` while SKILL.md
      wrapped it - closed (the reference now gives `str(item.get("ctx", {}).get("error"))`); no
      capture command named for the harness - declined, running the program's own outputs from
      the unmodified tree is the capture, and the shape varies per project
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion keeps its own subject
- [x] ASCII only; no private names in the added text (the incident's tool and project names are
      not used)

Decisions: d-20261115-bcadad3b, d-20261115-ef1a8c1c, d-20261115-ab79c091, d-20261115-b2d42dfc
