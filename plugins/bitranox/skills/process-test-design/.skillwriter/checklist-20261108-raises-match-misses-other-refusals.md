# skill-writer checklist - process-test-design (2026-11-08, raises match= misses other refusals)

- [x] Change: references/silent-test-defeaters.md, section "Harvest a `pytest.raises(match=...)`
      pattern per parametrized arm". New paragraph: a pattern must MISS every other refusal the
      code can raise (`match=` is `re.search`; grep every `raise` in the module and the layers it
      calls and check the pattern against each message; escape regex characters; anchor an inner
      rule's pattern with `^` against a wrapper that interpolates it; a test-raised sentinel gets a
      sentence matched whole). The first paragraph's "match only a substring every arm shares" now
      adds "and no other refusal contains (below)".
- [x] Receipt held (skill_receipt.py start meta-skill-writer); the editing agent loaded the skill.
- [x] Step 0b: `skill_decisions.py show process-test-design` printed nothing (no ledger yet), so no
      recorded decision is reversed.
- [x] RED, text check of the pre-edit artifact (`git show HEAD:` of the reference): the section
      asks to match the validator's phrase, never a piece of the input, and allows "a substring
      every arm shares"; no sentence asks to check a pattern against the code's other refusals.
- [x] RED, behavioural (opus and haiku, `baseline-probe`, pre-edit section pasted): both arms chose
      specific patterns and both planned a grep of the other `raise` sites, so the ACTION tied with
      GREEN. Their reasons: both listed under Skill gaps that the text does not ask for it ("It does
      not say to grep the other raise sites for a shared phrase"). The scenario telegraphed the trap
      ("other `raise` statements you have not looked at"), so the behavioural arm is contaminated;
      the text check above is the RED evidence.
- [x] GREEN (opus and haiku, edited section pasted, a review task with a loose alternation pattern
      and a one-word sentinel): both arms rejected both tests and quoted the deciding sentences
      verbatim ("`match=` is `re.search`, so a word several refusals share ... passes whichever of
      them fires", "A sentinel the test raises itself to end a block ... gets a sentence no other
      message contains, matched whole").
- [x] Gaps from GREEN: closed - a wrapper that interpolates a lower refusal (both tiers reported
      it); the new sentence was re-probed by quote-back on haiku and opus, both quoted "a pattern for
      the inner rule also passes when the wrapper fires: anchor it at the start (`^`)" and "a pattern
      for the wrapper includes the wrapper's own words". Declined: which clause of a two-clause
      message to match (the rule's wording, already stated in the section); a bare `^boom$` versus a
      sentence (the text asks for a sentence, both tiers read it so); how to prove RED for such a
      test (the skill's mutation guidance covers it, SKILL.md "mutate that code in a scratch copy");
      a `^` broken by an `[Errno N]` prefix (the pattern is taken from the printed message, and
      "require it to match its own" fails it); a wrapper that puts `{error}` first, how deep the
      grep goes (judgement left open).
- [x] Every mechanism claim executed: `re.search` with an unanchored inner pattern matches a
      wrapper message that interpolates it (True) and the `^`-anchored pattern does not (False).
- [x] GREEN diffed against RED both ways: RED's specific patterns and its other checks (pre-feature
      RED, mutation, liveness pair) are untouched by the edit; nothing lost.
- [x] Width and fence check over the added lines: nothing reported. The paragraph after the
      insertion ("A substring assertion on a reworded message must fail on the OLD message") holds
      no back-reference.
- [x] Tiers: opus and haiku for RED, GREEN and the quote-back re-probe (6 cells).
- Decisions: d-20261108-940b7602
- [x] Description measured: unchanged (SKILL.md not edited)
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII
