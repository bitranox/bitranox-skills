# skill-writer checklist - meta-skill-writer (2026-10-27, two queued improvement notes)

Two additions to SKILL.md:

1. "Code Examples": **Executing an example proves it on one platform only.** An example that
   filters or branches on a value a per-platform backend produces is checked per backend (read the
   mapping or run it on each supported platform), the platform limit is stated next to the
   example, and a platform that can be neither read nor run is named as unverified.
2. REFACTOR, after "Verify each fix by quote-back": **A quote-back proves the text is readable,
   never that it is true.** Before probing a touched paragraph, each mechanism claim in it is
   checked against the code it describes (grep the symbol, read the branch that raises or
   returns).

- [x] Receipt fresh for this session (`skill_receipt.py check meta-skill-writer`), skill loaded
      through the Skill tool before the first edit.
- [x] Skill type: technique/discipline guidance read as retrieval; the test is quote-back - what
      to do before shipping a platform-dependent example, where the limit goes, whether a
      correct quote-back shows a claim is true, when and how to check a mechanism claim.
- [x] RED by text check against the pre-change file (`git show HEAD:` of SKILL.md and
      testing-skills-with-subagents.md): no line matches per-platform, each platform, platform
      limit, one host, readable, mechanism claim, raising branch or against the code. A
      behavioural RED was not used: `redcheck --corpus-cascade` reported STRONG inherited
      coverage for both scenarios from this machine's always-loaded memory index (entries on
      executing doc examples, single-environment tools and quote-back verification), so the
      coverage check against the skill file is the evidence.
- [x] Claims verified before writing:
      - item 1 measured example: the library's macOS neighbour backend builds every entry with
        `state=NeighbourState.OTHER` (its dump reports no per-entry state), while the Linux
        backend maps kernel states; a Linux run of the REACHABLE filter returned 2 of 18 entries,
        so the count varies per run and the text says "the reachable entries" instead of a
        number.
      - item 2 measured example: the macOS DHCP capture refuses an interface whose BPF link type
        is not `DLT_EN10MB` with `IPScoutUnsupportedError`; no branch compares the interface
        name, so "refuses by name" is false and "refuses by the link type the device reports" is
        what the code does.
- [x] GREEN by quote-back on both passages (bitranox:baseline-probe, opus at effort medium plus
      haiku, 4 questions each): every answer a direct quote, no NONE, no contradiction.
- [x] Gaps, each decided:
      - what to do when a platform can be neither run nor read (opus, and haiku in part) -
        CLOSED: "where you can do neither for a platform, say there that the example is
        unverified on it".
      - which platforms "each platform" means (opus) - CLOSED: "each platform the library
        supports".
      - where the supported-platform list lives, where a backend's mapping lives, the wording of
        the limit note, whether to note anything when all platforms agree, ranking reading
        against running - DECLINED: judgement left to the author; it depends on the library.
      - how to recognise an example that depends on a backend value - DECLINED: the parenthetical
        "(a state, an address family, an interface name)" names the shape; a full list is not
        possible.
      - whether comments inside a code example count as mechanism claims, what "touched
        paragraph" covers, whether the code check repeats after the probe - DECLINED: plain
        reading; a comment stating a mechanism is a mechanism claim, and the check is on the
        text, which the probe does not change.
      - tension with "one great example is enough" - DECLINED: stating a platform limit next to
        one example needs no second example.
      - the cited "A pass gets the same re-run as a failure" was outside the excerpt - DECLINED,
        covered elsewhere: that section is in SKILL.md under GREEN.
- [x] Re-probe on the final item-1 text (opus at effort medium plus haiku, 3 questions): both
      tiers quote "each platform the library supports" and "where you can do neither for a
      platform, say there that the example is unverified on it."; remaining notes are the
      declines above, no new undecided gap.
- [x] quotecheck over the skill dir: 7 of 7 probe quotes OK, a planted invented sentence came
      back MISMATCH.
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku - 4 cells.
- [x] Description unchanged - no routing keyword moved; trigger map not rebuilt.
- [x] Tables: `reformat_tables.py --check --strict` reports SKILL.md unchanged.
- [x] Version-history finder over the skill dir: every hit is pre-existing (the rule's own text
      and vendored upstream doc), none in the added lines.
- [x] No address, MAC, hostname or machine path added; ASCII only; present tense.
- [x] Skill tests (`tests/`, 56 passed) and the repo's skill/description/trigger/tell hook tests
      (948 passed) green with CI's dependency set.
