# skill-writer checklist - compuse-toolbox (2026-10-12, pushcheck --denylist-file format)

The `pushcheck` row gains the `--denylist-file` line format. No other row or note changed;
frontmatter unchanged.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed sentence, answered only from the row text pasted into the prompt, with a verbatim
      quote or NONE.
- [x] Scope: one sentence inside the `pushcheck` row.
- [x] Inherited-context route: the arms were the inert `bitranox:baseline-probe` type answering
      from the pasted row only, so the result is a text check of the row, not of the installed
      skill or the machine's memory.

## RED (pre-change row, haiku)
- [x] Q1 pass a `#`-commented, `term==>replacement` list unchanged: NONE ("The row never describes
      the denylist file format").
- [x] Q2 the `#` line: NONE. Q3 what `Alpha Corp==>Org1` searches: NONE. Q4 leading spaces: NONE.
      Q5 does `ALPHA CORP` match: NONE.
- [x] Skill gaps asked for: RED listed the format, comments, `==>`, whitespace, case folding, and
      the refusal reason for an unusable list as unaddressed.

## GREEN (new row, same model and questions, plus a control)
- [x] Q1 unchanged, quoting "so one list serves both jigs unchanged"; Q2 a comment, quoting "a line
      whose first non-blank character is `#`, is a comment"; Q3 the term before `==>`; Q4 stripped,
      quoting "every term is stripped of surrounding whitespace"; Q5 yes, quoting "found as a
      case-insensitive substring by casefold".
- [x] Control Q6 (an RFC5737 address is not a finding) answered from the unchanged sentence, as
      before the edit.
- [x] GREEN gap closed: whether the replacement side is used. The row now says the rule "ignores
      the replacement"; verified by quote-back.
- [x] Gaps declined, with reasons: a denylist term that is itself a documentation-range value (the
      denylist is a separate substring scan; an operator does not list RFC5737 values as private);
      a `==>x` rule with an empty term and the order comment-then-rule on one line (parser detail,
      stated in the script's docstring and covered by tests; the zero-term refusal covers a list
      made only of such lines); which version the row documents (the row describes the shipped
      jig of the same release).
- [x] GREEN diffed against RED in both directions: no RED answer was a quote, so nothing was lost;
      the control is unchanged.

## Code the text describes
- [x] Every claim in the new sentence has a test in `tests/test_pushcheck.py`: a comment line is not
      a term, a rule finds the name before the separator, padding stripped and matched
      case-insensitively, the sharp-s spelling found by a rule from the file, a non-UTF-8 list is a
      typed refusal, a list parsing to zero terms is refused.
- [x] The same release makes `Rule.digest` hash `fold_case(pattern)`: new test
      `test_a_rule_digest_folds_case_the_way_the_rule_matches` failed on `.lower()` (RED) and passes
      after the fix.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added; list values are placeholders.
- [x] Frontmatter untouched: no routing keyword moved.
