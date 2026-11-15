# skill-writer checklist - coding-data-architecture (2026-11-15, analyser and fixer brief rules)

Change: seven rules for the workflow's briefs and exceptions. The key-set pin reads the real table
object; a boundary DECODE table is permitted; a refusal's `<reason>` may be the library's per-error
message; a literal-only parameter stays a call-site-sweep finding even when it only reaches a
message; findings are checked against the repo's recorded decisions before a brief; a fixer
turning a tuple into a record updates every consumer and names fields for what they hold; the
error-surface diff has one liveness control per entry point and prints every case before counting
"same". The NOT-violations list in STEP A carries the three permitted shapes.

- [x] Receipt held (skill_receipt.py check: fresh); this agent loaded meta-skill-writer itself
- [x] Step 0b: `skill_decisions.py show coding-data-architecture --kind rejected,removed --full`
      printed nothing, so no recorded decision is reversed
- [x] RED (text check, pre-edit file from `git show HEAD:`): an `opus` quote-back probe over the
      pre-edit text answered the seven questions with neighbouring text only and its Skill gaps
      named each rule as absent: no per-entry-point liveness count, no decisions-log check, pin
      test silent on copy vs real table, decode tables "undecided", per-error message "not
      stated", message-literal exclusion "neither granted nor refused", tuple consumers absent
- [x] GREEN: quote-back over the post-edit text on `opus` (effort medium) and `haiku`; both tiers
      quoted the new governing lines for all seven questions (14 questions x 2 tiers over the
      five files of this change; 7 belong to this skill)
- [x] Skill gaps from GREEN: Q2 "two" is inferred from "for EACH entry point ... are two" -
      declined, the count follows from the sentence; Q3 a reader could misread the message-literal
      exclusion - declined, the same sentence states the parameter case explicitly; Q5 how a
      `tests/` pin reaches a public table - declined, the python skill covers private tables by
      doctest and a public table is importable
- [x] Width and fence check over the added lines printed nothing; paragraphs after each
      insertion read for re-bound references (none); the NOT-violations sentence still ends with
      its "Without this" consequence
- [x] ASCII only; no private names, hosts or paths in the added text
- [x] CSO description unchanged (body edit only)

Decisions: d-20261115-75ccfe41, d-20261115-b0e3e9db, d-20261115-f4b1c4bf, d-20261115-52c89e75, d-20261115-bbfa080e, d-20261115-ba6a9eed, d-20261115-dc5b6bbb
