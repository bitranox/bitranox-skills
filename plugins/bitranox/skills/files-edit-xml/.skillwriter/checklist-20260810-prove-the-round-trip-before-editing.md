# files-edit-xml: prove the round-trip before editing a file you must diff

Scope: one new section plus its table. No code change in this skill.

Triggered by a real incident: editing a pfSense `config.xml` with the skill's existing pattern
produced a **6863-line diff for a 6-line change**. The output was well-formed and the skill was
followed correctly - it simply does not distinguish "valid" from "reviewable", and on a production
firewall config an unreviewable diff is how a real mistake gets approved.

## What the tests showed

- [x] Coverage checked before writing: the skill is 402 words and teaches parse, edit, serialize,
      re-parse. Its only CDATA mention is inside the sentence explaining why hand-editing breaks.
      Nothing about minimal diffs, empty-tag collapse, or round-trip proof. Genuinely additive.
- [x] The three losses are lxml choosing legal equivalents, not bugs, so they are stated as
      behaviour to normalise rather than as defects to report upstream.
- [x] The rule is stated as an executable assertion (`assert serialize(tree) == original`) rather
      than as advice, so a reader either has a passing check or does not.
- [x] Generalised one step, deliberately and no further: the same "round-trip the untouched file and
      require zero diff" test applies to JSON key order and YAML quoting. Not extended to formats
      where the claim was not verified.
- [x] ASCII only, no typographic tells. The table was reformatted by the repo's own table hook after
      the edit, and re-checked afterwards.

## Checks

- [x] Version bumped 5.164.3 -> 5.164.4, PATCH per this repo's SemVer note ("wording/doc fix in a
      skill"); this ships alongside a guard bug fix in the same release.
- [x] Bump and changelog both verified by re-reading the files after writing, not by the script
      reporting success - a silent no-op bump shipped an unbumped change earlier in this session.
- [x] Marketplace history stays append-only: additive commit, no squash, no force-push.

## Note for the next editor

The measured number (6863) is load-bearing and should not be rounded away or restated as "a large
diff" - it is what makes the section persuasive enough to act on before the mistake, rather than
after.
