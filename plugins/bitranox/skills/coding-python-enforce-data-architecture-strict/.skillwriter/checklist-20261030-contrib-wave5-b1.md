# Review checklist: coding-python-enforce-data-architecture-strict (2026-10-30)

Covered:

1. A `str, Enum` member reaching a log, event or payload builder through a `str` parameter - new
   paragraph in "The `str, Enum` fallback formats differently on 3.10 and 3.11+".
2. A raw string breaks every reader of `.value`; a public constructor field narrowed to the Enum
   parses at construction - third bullet in "Converting a `str` parameter to an Enum changes its
   contract", with the closing sentence widened to cover it.
3. STEP D may let agents under-report - STEP D now requires one verdict line per hit naming the
   exclusion, and routes a real finding into the state file and STEP B instead of STEP A; the
   LOOP ENFORCEMENT block gained that path.
4. Not changed (ALREADY): "run your own sweep for `-> tuple[` after the analyser fan-out" is STEP A's
   CANDIDATE SWEEP bullet.

## Evidence

- [x] Item 1 run on 3.10 and 3.14: a `class Layer(str, Enum)` member passed through
      `def ctx(layer: str) -> dict` rendered `'%s'` -> `Layer.DEFAULTS` on both, f-string ->
      `defaults` on 3.10 and `Layer.DEFAULTS` on 3.14, `json.dumps` -> `"defaults"` on both.
- [x] Item 2 run: a frozen dataclass field typed `Layer` built with `cast('Layer', 'user')`:
      `== Layer.USER` True, dict lookup worked, `.value` raised
      `AttributeError: 'str' object has no attribute 'value'`. With
      `__post_init__: object.__setattr__(self, 'name', Layer(self.name))` the same call gave
      `.value == 'user'`, a member stayed `is Layer.USER`, and `'bogus'` raised `ValueError`.
- [x] Item 3, blind review: 20 STEP D signature hits drawn with a fixed seed from the 121
      def-line dict hits the agents had all labelled clean (10 a second classifier scored
      >= 0.5, 10 below). Three `opus` judges, given the skill's own rule text and no scores,
      agreed on every item: 4 real (two hand-built fixed-key `wire()` dicts, two untyped
      `dict[str, Any]` TOML tables returned across a function), 16 permitted. All 4 were in the
      >= 0.5 half. So the agents did under-report, but far less than the classifier implied.
- [x] Item 3, RED arms on the PRE-edit STEP D text (pressure: loop at zero, user wants it
      finished): haiku and opus on 4 hits both judged the two real shapes real and the two
      permitted ones permitted; a haiku arm on all 20 hits called the same 4 real plus 2
      enum-keyed lookup tables. The verdict wording did not reproduce the under-report. All three
      arms named one gap: "GOTO STEP A" sends a STEP D finding back to analysers that already
      passed that line, so the text gives no way to act on it. That gap is what the edit closes,
      together with a per-hit verdict line naming the exclusion (evidence instead of a verdict).
- [x] Item 3, GREEN arm (haiku, new STEP D text, 2 hits): wrote one verdict line per hit with the
      exclusion named, recorded the real hit in the state file as `in_progress`, and went to STEP
      B quoting "Not STEP A: its analysers already passed that line as clean". It ran on the
      wording before the SCOPE attribution sentence was added; that sentence only routes an
      out-of-scope hit to the existing `out_of_scope` list (checked by reading, not re-probed).
- [x] Items 1 and 2, GREEN arm (haiku, excerpts pasted): Q2 typed the builder parameter as the
      Enum and took `.value` inside, quoting "type the parameter as the Enum and take `.value`
      INSIDE the builder"; Q3 named the AttributeError and the `__post_init__` parse.
- [x] Skill gaps, each decided:
      - "Core Principle 7 vs the constructor parse is not reconciled" - CLOSED: the bullet now
        says the parse is an outside caller's input parsed once at entry, not a Principle 7 shim.
      - "Enum-keyed lookup tables (`dict[FillPattern, ...]`) - real or permitted?" - left open:
        the judges called them permitted, one RED arm called them real; the rule is silent and
        the case was not part of the reported defect, so it is not decided here.
      - "Which wins: total_violations == 0 or a real hit" - declined: the new bullet says the
        analysers' zero is not evidence about a hit, and a real hit takes the STEP B path.
      - "What follows STEP A after the fix" - declined: LOOP ENFORCEMENT states the full loop.
      - "The grep misses `Dict[`, `Mapping[`" - declined: out of scope of this change.
- [x] Width and fence check over the added lines printed nothing; paragraphs after each insertion
      were read (the old "If either kind of test exists" became "any of these kinds").
- [x] ASCII only; front matter parses with `yaml.safe_load`; tables canonical.
- [x] No private paths, hosts, repo names or session details.
