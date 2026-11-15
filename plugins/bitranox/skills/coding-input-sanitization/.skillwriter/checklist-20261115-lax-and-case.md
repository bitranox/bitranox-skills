# skill-writer checklist - coding-input-sanitization (2026-11-15, lax numeric text and per-character case rules)

Change: two "On the way IN" bullets plus one Quick checklist line. A lax-mode Pydantic field is not
a check on numeric or date text from a query or form; check the raw string or use a constrained
`str` field. An "upper case only" rule is written per character, so characters whose upper case is
longer than one character (sharp s, the U+FB00-U+FB06 ligatures) are accepted.

- [x] Receipt held; this agent loaded meta-skill-writer itself
- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill
- [x] Claims executed (pydantic 2.14.3): an `int` field accepted `"1_0"` (10), `"+2"`, `" 7 "` and
      a 200-zero padded value; a `Decimal` field accepted `"1e3"`, `"1_0"`, Arabic-Indic digits
      and 200 leading zeros under `max_digits=5`; a `date` field accepted midnight datetime strings
      with and without an offset, and a `time` field an offset. The queued lesson said `int`
      accepts Arabic-Indic digits: measured REFUSED (`int_parsing`), so the text names `Decimal`
      only. `chr(0xDF).upper() == "SS"`, U+FB00-U+FB06 upper-case to 2 or 3 letters; the
      per-character predicate returned False for sharp s and U+FB01 and True for `a`
- [x] RED (pre-edit text, `opus` quote-back): Skill gaps said nothing covers lax `int`
      underscores/whitespace/non-ASCII digits, and the case rule question was "silent"
- [x] GREEN: `opus` (effort medium) and `haiku` both quoted the two new bullets
- [x] Skill gaps from GREEN: no refuse-side test case for the case rule - closed (a lower-case
      ASCII letter on the refuse side); no response shape for a refused page number - declined,
      out of scope for this rule (the refusal path is the project's own)
- [x] Width and fence check over the added lines printed nothing; a word split across a line end
      by a hyphen was rejoined
- [x] ASCII only; the incident's project names are not used

Decisions: d-20261115-bbb632cf, d-20261115-45d496ee
