# Review checklist 2026-10-30: Enum-keyed lookup tables

Change: a lookup table keyed by a closed Enum is a named exception to Core Principle 3 when it is
read-only, keyed by the Enum itself, fully typed in its values, and a test pins every member. The
policy is a user decision (permitted, with those four conditions). STEP D gains a second grep for
module-level `Mapping[...]` / `Final[dict[...]]` tables.

Files: `SKILL.md` (Core Principle 3, the Exceptions list, STEP D).

## Claims and their evidence

- [x] Read-only needs `MappingProxyType`, measured with pyright strict on a scratch module (a
      deliberate `return "no"` from a `-> int` function as the control, reported; files analysed
      1): `T: Final[Mapping[P, str]] = {...}` then `T[P.A] = "z"` inside a function reports no
      error; the same write on `Final[Mapping[P, str]] = MappingProxyType({...})` reports
      `"__setitem__" method not defined on type "MappingProxyType[P, str]"`.
- [x] The new grep `^[A-Za-z_][A-Za-z0-9_]*: .*(dict|Mapping)\[`, run on a sample: matches the
      five module-level tables (`Final[Mapping[`, `dict[`, `Final[dict[`), not a function
      signature, an indented local dict or `count: int = 0`.

## Probes (bitranox:baseline-probe, text only, opus and haiku, 2 tiers x 3 rounds = 6 cells)

- [x] RED (pre-edit text, `git show HEAD`): both tiers called the compliant table (Enum key,
      `MappingProxyType`, member-pinning test) real, quoting "Small local dicts (few items, single
      function scope) may remain - convert if used across functions/modules"; both gaps lists
      said the text was silent on Enum-keyed lookup tables.
- [x] GREEN: both tiers: compliant table permitted (quoting the new bullet), mutable `Any`-valued
      accumulator real, `str`-keyed table real (quoting "A table keyed by `str` spellings ... key
      it by the Enum"), table without a member test real, `Final[dict]` table real.
- [x] Final re-probe on the final text: both tiers the same verdicts plus `Final[Mapping]` over a
      plain dict literal real (quoting "The proxy is not optional ..."), and both named the new
      grep as what surfaces those tables, quoting it.

## Gaps closed

- Principle 3 and the Exceptions read as contradictory: Principle 3 now says the listed kinds
  are exempt from it.
- "Read-only" read as examples rather than a conjunction: now "takes all three of".
- The STEP D greps could not surface `Mapping[...]` or `Final[dict[...]]` tables: second grep.

## Gaps declined

- Add `Mapping[` to the signature grep: it would surface annotations the skill prescribes (the
  recursive `JsonValue` alias, the `Mapping[str, Any]` pass-through), which no exclusion names,
  so they would be judged real.
- Widen the new grep to indented lines (class attributes): `^\s*` also matches multi-line
  signature parameters such as `opts: Mapping[str, Any],`, the same conflict.
- Whether a Mapping annotation alone blocks the write in another function: measured above, it
  does not when the name is `Final` and holds a dict literal.
- Where the member test lives, how "nothing writes to it" is checked beyond the proxy, the fix
  for a failing table, and `real` vs `violation`: covered by "add the missing property or
  convert the table" and "A hit that fits no named exclusion is real", or judgement the text
  leaves to the reviewer.

## Mechanical checks

- [x] Added lines: none over 100 columns except Core Principle 3, whose list keeps each principle
      on one line (Principle 4 is several hundred columns); no fence opened or left open.
- [x] The paragraph after each insertion read: "**Verification:**" after the Exceptions, and
      "Write one verdict line per hit" after the new STEP D bullet; no re-bound reference.
- [x] Description unchanged, so the trigger map and catalogue need no regeneration.
