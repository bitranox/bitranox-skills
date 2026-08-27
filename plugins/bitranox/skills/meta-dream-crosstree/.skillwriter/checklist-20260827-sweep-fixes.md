# skill-writer checklist - meta-dream-crosstree (2026-08-27, sweep fixes)

Four corrections: two contradicted the shared reference this skill itself cites as authoritative.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] Scope: `dream-core.md`'s ladder says meta-dream-tree is "ONE knowledge tree, TREE-WIDE (every
      level under the anchor)". This skill said it "tidies ONE project's store" - a tree spans
      sibling projects, so the line understated it. Corrected to tree-wide.
- [x] Promotion gate: the "same-project >= 2-dreams dwell" attributed to meta-dream-tree does not
      exist; both dreams read the same distinct-project store. Corrected, and the idempotence stated.
- [x] Content-hash: no content-hash item dedup exists. The only `hashlib` uses in reach
      (`gather_scan.py`) hash a PATH for a cache filename. Replaced with the ancestor-overlap check
      and a pointer to dream-core.md's "Dedup semantics", which this skill already cites.
- [x] Dangling ref: `references/dream-passes.md` does not exist here (this skill dir holds only
      SKILL.md). Now skill-qualified to meta-dream-tree, matching the sentence immediately before it.
