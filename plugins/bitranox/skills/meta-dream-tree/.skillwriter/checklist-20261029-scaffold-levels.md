# skill-writer checklist - meta-dream-tree (scaffold-noise levels are set aside, never proposed for removal)

- [x] Change: SKILL.md step 0b and its deliverable line, and the Boundaries list in
      references/dream-core.md. A scaffold-noise level is listed as set aside with nothing to
      decide; it is no longer proposed for removal, because the SessionStart self-heal
      (session-start.py `_self_heal` calling `memory_engine.heal` on the session's cwd) recreates
      every level of that chain on each start. A level minted in a throwaway dir becomes a
      contribution against the minting hook.
- [x] Mechanism checked against the code: `_self_heal(proj)` runs on every SessionStart and calls
      `memory_engine.heal(proj)`, which walks `sig.altitude_chain(proj)` and recreates the marker
      and pointer block at each level.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); the edit was made by the agent that
      loaded the skill.
- [x] redcheck --corpus-cascade on the scenario: term-overlap hits only (the tree-top memory index
      and two facts on SessionStart writes and scope descriptors); none states that the dream must
      not propose removing scaffold levels. Route kept: a behavioural arm on pasted text, plus the
      text check below.
- [x] Text check against the pre-edit file: the old step 0b says "PROPOSE its removal as a
      structural move", the old deliverable "listed as a proposed removal".
- [x] RED, old text pasted, haiku and opus (2 cells): both listed the four levels as proposed
      removals and asked the user to decide; haiku recommended removal. opus reported in its gaps
      that the removal may not stick because heal recreates the level.
- [x] GREEN, new text pasted, haiku and opus (2 cells): both listed the four levels as set aside,
      asked nothing, and quoted "List it in the report as set aside, with nothing for the user to
      decide."; both routed the throwaway run dir to a contribution against the minting hook.
- [x] GREEN gaps decided:
      - The recreation reason holds only if a session starts there again (opus). CLOSED: step 0b
        now says one already ran there and the dream cannot tell whether another will.
        Quote-back on haiku: "No" to proposing removal of a level believed abandoned, with a
        direct quote of the new sentence.
      - No harm test and no named hook for the throwaway case. DECLINED: a judgement the skill
        leaves open; how to queue a contribution is owned by meta-self-improve.
      - Report line format not given. DECLINED: the report format is the dream's own, not this
        step's.
      - Which file holds the descriptor block. DECLINED: covered by the storage spec
        (meta-self-improve references/memory-backend.md) and unchanged by this edit.
      - A noise dir that should become a real level. DECLINED: covered in the same step ("a
        descriptor but no pointers is usually a real level not used yet"); a level that gains
        pointers is no longer noise.
- [x] GREEN against RED in both directions: nothing the baseline produced is lost; the descriptor
      and level-count exclusions hold in all four cells.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, added prose wrapped to the file's width, no table touched.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
