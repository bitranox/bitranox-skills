# skill-writer checklist - process-test-design (2026-10-16, rules folded into the skill)

- [x] Change, one line per item:
  - Unlinked file: SKILL.md now points at `references/silent-test-defeaters.md` (paragraph before
    "Quick checklist"), naming the triggers from the reference's own opening paragraph.
  - Contradiction (loop bound vs "No timer in a test"): the reference entry now says the first
    choice is blocking on a signalled event, scopes the bound to the loops that remain (a
    production loop driven by a fake, a cooperative-task spin with no event to plant), and requires
    a COUNT bound, never a wall-clock deadline. SKILL.md's rule is unchanged.
  - Contradiction (two remedies for `from m import X`): both texts now give the same ordered
    remedies - inject; read the qualified `m.X` at call time when you own the reader; else patch
    at the consumer. The SKILL.md bullet names the other three early bindings and points to the
    reference.
  - Rules to add: none listed for this skill.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the
      skill through the Skill tool before its first edit
- [x] RED (text check of the artifact): before this edit SKILL.md had no link to the reference
      (verifier: "grep for 'silent-test-defeaters' or 'references/' in SKILL.md returns nothing"),
      the reference endorsed a spin loop with no precedence over the SKILL.md "No timer in a test"
      rule, and the `from m import X` mechanic carried different fixes in the two texts. A
      behavioural RED was replaced on purpose: these rules are in the always-loaded memory index of
      the authoring machine (inherited coverage), so a behavioural arm answers from that context
      with or without this text.
- [x] GREEN quote-back (fresh-context verifier): C1 -> SKILL.md "Read
      `references/silent-test-defeaters.md` (Read tool) when a test patches a name ..."; C3 ->
      SKILL.md "Best, inject ...; where you own the reader, read the qualified `m.X` at call time";
      C2 closed after verification: the "No timer in a test" paragraph now names the one exception,
      "a COUNT-bounded spin (a zero-duration yield such as `await asyncio.sleep(0)`, which yields
      rather than waits)", and points at the reference.
- [x] Gaps closed or declined: C2 closed as above; no other gaps.
- [x] Description measured: unchanged, 658 characters
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
