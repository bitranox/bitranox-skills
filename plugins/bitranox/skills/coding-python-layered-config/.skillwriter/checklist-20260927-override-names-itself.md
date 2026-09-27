# skill-writer checklist - coding-python-layered-config (2026-09-27, override names itself)

lib_layered_config 5.7.0 changes `Config.with_overrides` so every key an override supplies reads
back as layer `override`, path `None`. The skill taught the previous behaviour as the library's
contract, and its remedy (rebuild provenance in every caller) as mandatory.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The change corrects a claim about library behaviour, so the test is
      the claim checked against the executed library, plus a quote-back.
- [x] Scope: one paragraph of the provenance section rewritten; the rebuild recipe kept for an
      older floor or a `cli` label. No frontmatter change, no routing keyword moved.
- [x] Mirrored pair: the twin `libs/lib_layered_config/skills/python-layered-config` carries the
      identical paragraph; a direct diff of the two files differs only in the `name:` field.

## RED
- [x] Behavioural RED not used: `redcheck --corpus-cascade` over the library repo returned
      INHERITED COVERAGE (STRONG), naming the memory fact that recorded the old behaviour and its
      pointer line. An agent dispatched here answers from that fact, so the arm cannot fail
      honestly. That fact was corrected in the same change.
- [x] Text RED against the executed library: the skill said `with_overrides` "returns the merged
      data with the ORIGINAL provenance map" (1 hit), while running the call on 5.7.0 returned
      `{'layer': 'override', 'path': None, 'key': 'db.host'}`.

## GREEN
- [x] The skill's code block was executed against the library and its stated output compared
      byte for byte: MATCH.
- [x] Quote-back on the haiku tier, four questions, each answered with the governing sentence:
      a 5.7.0 floor needs no rebuild; a 5.4.0 floor does ("Before 5.7.0 it returned the ORIGINAL
      provenance map"); a key removed by a scalar has no source; a `cli` label means rebuilding.

## REFACTOR
- [x] Skill gaps from GREEN: (1) `origin("db")` after a scalar replaced the table was only
      inferable, (2) "no rebuild needed on 5.7.0" was only implied. Both closed in the text
      ("the scalar's key (`db`) reads as `override`"; "a caller content with that label needs no
      provenance code of its own") and re-verified by quote-back on the two touched questions.
- [x] Declined: the second run noted that the exact dict for `origin("db")` is shown only by the
      example's form. The example states the shape once; repeating it per case adds length for no
      decision a reader makes differently.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added; `/etc/app.toml` is a generic example.
- [x] Frontmatter untouched, so the description cap is unaffected.
